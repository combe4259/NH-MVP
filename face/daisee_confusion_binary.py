"""
DAiSEE Confusion Binary Classification Model
Trains a binary classifier for confusion detection (0: Not Confused vs 1~3: Confused)
"""

import os
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
import torchvision.transforms as transforms
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from typing import List, Tuple, Dict
from tqdm import tqdm
import glob

# GPU configuration (uses MPS for Mac M3 Pro, CUDA for NVIDIA GPUs, or CPU)
if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")
print(f"Using device: {device}")

class LocalDAiSEEConfusionDataset(Dataset):
    """Local DAiSEE Dataset for Confusion Binary Classification"""
    
    def __init__(self, 
                 data_root: str = "/Users/inter4259/Desktop/NH/DAiSEE",
                 subset: str = 'Train',
                 sequence_length: int = 30,
                 image_size: Tuple[int, int] = (112, 112),
                 max_samples: int = None):
        """
        Args:
            data_root: DAiSEE root directory
            subset: 'Train', 'Test', or 'Validation'
            sequence_length: Number of frames to extract from each video
            image_size: Image dimensions (height, width)
            max_samples: Maximum number of samples (for testing)
        """
        self.data_root = data_root
        self.subset = subset
        self.sequence_length = sequence_length
        self.image_size = image_size

        # Load label file
        labels_file = os.path.join(data_root, "Labels", f"{subset}Labels.csv")
        print(f"Loading labels from {labels_file}...")
        self.labels_df = pd.read_csv(labels_file)

        # Strip whitespace from column names
        self.labels_df.columns = self.labels_df.columns.str.strip()
        print(f"Columns: {self.labels_df.columns.tolist()}")

        # Match video paths with labels
        self.video_paths = []
        self.labels = []

        video_dir = os.path.join(data_root, "DataSet", subset)
        print(f"Searching for videos in {video_dir}...")

        # Find existing video files
        found_count = 0
        missing_count = 0

        # Count confusion distribution
        confusion_counts = {0: 0, 1: 0}
        
        for idx, row in tqdm(self.labels_df.iterrows(), total=len(self.labels_df), desc="Loading videos"):
            clip_id = row['ClipID']
            # Remove .avi extension
            if clip_id.endswith('.avi'):
                clip_id = clip_id[:-4]

            # Split user ID and video ID (e.g., 1100011002 -> 110001, 1002)
            user_id = clip_id[:-4]
            video_id = clip_id[-4:]
            full_video_id = user_id + video_id

            # Video file path
            video_path = os.path.join(video_dir, user_id, full_video_id, f"{full_video_id}.avi")

            if os.path.exists(video_path):
                self.video_paths.append(video_path)

                # Convert confusion to binary label (0 -> 0, 1~3 -> 1)
                confusion_level = row['Confusion']
                binary_label = 1 if confusion_level > 0 else 0
                self.labels.append(binary_label)

                confusion_counts[binary_label] += 1
                found_count += 1

                if max_samples and found_count >= max_samples:
                    break
            else:
                missing_count += 1
        
        print(f"Found {found_count} videos")
        if missing_count > 0:
            print(f"Warning: Missing {missing_count} videos")

        # Print binary classification distribution
        total = sum(confusion_counts.values())
        if total > 0:
            print(f"\nConfusion Binary Distribution:")
            print(f"  Not Confused (0): {confusion_counts[0]} ({confusion_counts[0]/total*100:.1f}%)")
            print(f"  Confused (1~3):   {confusion_counts[1]} ({confusion_counts[1]/total*100:.1f}%)")

        # Preprocessing transforms
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(image_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                              std=[0.229, 0.224, 0.225])
        ])
    
    def __len__(self):
        return len(self.video_paths)
    
    def __getitem__(self, idx):
        """Load video and label"""
        video_path = self.video_paths[idx]
        label = self.labels[idx]

        # Load video
        frames = self.load_video(video_path)

        return frames, label

    def load_video(self, video_path: str) -> torch.Tensor:
        """Load video file and extract frames"""
        cap = cv2.VideoCapture(video_path)

        # Get total number of frames
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames == 0:
            print(f"Warning: Cannot read video {video_path}")
            cap.release()
            return torch.randn(self.sequence_length, 3, *self.image_size)

        # Select frame indices at uniform intervals
        if total_frames < self.sequence_length:
            indices = list(range(total_frames)) * (self.sequence_length // total_frames + 1)
            indices = indices[:self.sequence_length]
        else:
            indices = np.linspace(0, total_frames-1, self.sequence_length, dtype=int)
        
        frames = []
        for frame_idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if ret and frame is not None:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = self.transform(frame)
                frames.append(frame)
            else:
                if frames:
                    frames.append(frames[-1])
                else:
                    frames.append(torch.zeros(3, *self.image_size))
        
        cap.release()
        
        return torch.stack(frames)


class DAiSEEConfusionNet(nn.Module):
    """CNN-LSTM model for binary confusion classification"""

    def __init__(self, hidden_dim=256, num_layers=2):
        super(DAiSEEConfusionNet, self).__init__()

        # MobileNetV2 backbone
        self.cnn = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
        self.cnn.classifier = nn.Identity()
        self.feature_dim = 1280

        # Freeze some layers
        for param in list(self.cnn.parameters())[:-10]:
            param.requires_grad = False

        # LSTM layer
        self.lstm = nn.LSTM(
            input_size=self.feature_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.3 if num_layers > 1 else 0
        )

        # Attention mechanism
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.Tanh(),
            nn.Linear(128, 1),
            nn.Softmax(dim=1)
        )

        # Binary classification head (2 classes: Not Confused, Confused)
        self.classifier = nn.Linear(hidden_dim, 2)

        self.dropout = nn.Dropout(0.3)
    
    def forward(self, x):
        batch_size, seq_len, c, h, w = x.size()

        # Extract CNN features
        x = x.view(-1, c, h, w)
        features = self.cnn(x)
        features = features.view(batch_size, seq_len, -1)

        # LSTM processing
        lstm_out, _ = self.lstm(features)

        # Apply attention
        attention_weights = self.attention(lstm_out)
        attended = torch.sum(lstm_out * attention_weights, dim=1)

        # Dropout regularization
        attended = self.dropout(attended)

        # Binary classification
        output = self.classifier(attended)

        return output


def train_confusion_model(num_epochs=10, batch_size=8, max_samples=None):
    """Train confusion binary classification model"""

    print("=" * 50)
    print("Confusion Binary Classification Training")
    print("(0: Not Confused vs 1: Confused)")
    print("=" * 50)

    # Create datasets
    print("\nLoading datasets...")
    train_dataset = LocalDAiSEEConfusionDataset(
        subset='Train',
        max_samples=max_samples
    )

    val_dataset = LocalDAiSEEConfusionDataset(
        subset='Validation',
        max_samples=min(500, max_samples) if max_samples else None
    )

    # Create DataLoaders
    train_loader = DataLoader(
        train_dataset, 
        batch_size=batch_size, 
        shuffle=True,
        num_workers=0
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size * 2,
        shuffle=False,
        num_workers=0
    )
    
    print(f"Train samples: {len(train_dataset)}")
    print(f"Validation samples: {len(val_dataset)}")

    # Create model
    print("\nCreating model...")
    model = DAiSEEConfusionNet().to(device)

    # Class weights for imbalance correction
    # Not Confused: 67.5%, Confused: 32.5% -> weight ratio 1:2.1
    class_weights = torch.tensor([1.0, 2.1]).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', patience=3, factor=0.5
    )

    # Training loop
    print("\nStarting training...")
    best_val_acc = 0
    
    for epoch in range(num_epochs):
        # Training
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0
        
        progress_bar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{num_epochs}")
        
        for batch_idx, (frames, labels) in enumerate(progress_bar):
            frames = frames.to(device)
            labels = labels.to(device)
            
            # Forward
            outputs = model(frames)
            loss = criterion(outputs, labels)
            
            # Backward
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()


            # Calculate accuracy
            _, predicted = torch.max(outputs, 1)
            train_total += labels.size(0)
            train_correct += (predicted == labels).sum().item()

            train_loss += loss.item()

            # Update progress bar
            progress_bar.set_postfix({
                'loss': f'{loss.item():.4f}',
                'acc': f'{train_correct/train_total*100:.2f}%'
            })

        # Validation phase
        model.eval()
        val_loss = 0
        val_correct = 0
        val_total = 0

        # Variables for confusion matrix
        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0
        
        with torch.no_grad():
            for frames, labels in tqdm(val_loader, desc="Validation"):
                frames = frames.to(device)
                labels = labels.to(device)
                
                outputs = model(frames)
                loss = criterion(outputs, labels)
                
                _, predicted = torch.max(outputs, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
                val_loss += loss.item()

                # Calculate confusion matrix
                for i in range(labels.size(0)):
                    if labels[i] == 1 and predicted[i] == 1:
                        true_positives += 1
                    elif labels[i] == 0 and predicted[i] == 1:
                        false_positives += 1
                    elif labels[i] == 0 and predicted[i] == 0:
                        true_negatives += 1
                    elif labels[i] == 1 and predicted[i] == 0:
                        false_negatives += 1

        # Calculate averages
        avg_train_loss = train_loss / len(train_loader)
        avg_val_loss = val_loss / len(val_loader)
        train_acc = train_correct / train_total * 100
        val_acc = val_correct / val_total * 100

        # Calculate performance metrics
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        print(f"\nEpoch {epoch+1}/{num_epochs}")
        print(f"Train Loss: {avg_train_loss:.4f}, Train Acc: {train_acc:.2f}%")
        print(f"Val Loss: {avg_val_loss:.4f}, Val Acc: {val_acc:.2f}%")
        print(f"Precision: {precision:.3f}, Recall: {recall:.3f}, F1: {f1:.3f}")


        # Display confusion matrix
        print(f"\nConfusion Matrix:")
        print(f"              Predicted")
        print(f"              No  Yes")
        print(f"Actual No  [{true_negatives:4d} {false_positives:4d}]")
        print(f"       Yes [{false_negatives:4d} {true_positives:4d}]")

        # Adjust learning rate
        scheduler.step(avg_val_loss)

        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), 'confusion_binary_model.pth')
            print(f"Best model saved (Val Acc: {val_acc:.2f}%)")

    print(f"\nTraining completed. Best validation accuracy: {best_val_acc:.2f}%")
    return model


def test_confusion_model(model_path='confusion_binary_model.pth', max_samples=None):
    """Evaluate the trained model on test data"""

    print("\n" + "=" * 50)
    print("Testing Confusion Binary Model")
    print("=" * 50)

    # Load test dataset
    test_dataset = LocalDAiSEEConfusionDataset(
        subset='Test',
        max_samples=max_samples
    )
    
    test_loader = DataLoader(
        test_dataset,
        batch_size=8,
        shuffle=False,
        num_workers=0
    )


    print(f"Test samples: {len(test_dataset)}")

    # Load model
    model = DAiSEEConfusionNet().to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    print(f"Model loaded from {model_path}")

    # Evaluation
    correct = 0
    total = 0
    true_positives = 0
    false_positives = 0
    true_negatives = 0
    false_negatives = 0
    
    with torch.no_grad():
        for frames, labels in tqdm(test_loader, desc="Testing"):
            frames = frames.to(device)
            labels = labels.to(device)
            
            outputs = model(frames)
            _, predicted = torch.max(outputs, 1)


            total += labels.size(0)
            correct += (predicted == labels).sum().item()

            # Calculate confusion matrix
            for i in range(labels.size(0)):
                if labels[i] == 1 and predicted[i] == 1:
                    true_positives += 1
                elif labels[i] == 0 and predicted[i] == 1:
                    false_positives += 1
                elif labels[i] == 0 and predicted[i] == 0:
                    true_negatives += 1
                elif labels[i] == 1 and predicted[i] == 0:
                    false_negatives += 1

    # Display results
    accuracy = correct / total * 100
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    print("\nTest Results:")
    print("-" * 30)
    print(f"Accuracy:  {accuracy:.2f}%")
    print(f"Precision: {precision:.3f}")
    print(f"Recall:    {recall:.3f}")
    print(f"F1 Score:  {f1:.3f}")
    
    print(f"\nConfusion Matrix:")
    print(f"              Predicted")
    print(f"              No  Yes")
    print(f"Actual No  [{true_negatives:4d} {false_positives:4d}]")
    print(f"       Yes [{false_negatives:4d} {true_positives:4d}]")
    
    return accuracy


if __name__ == "__main__":
    print("Confusion Binary Classification Model")
    print("=" * 50)
    
    # 옵션 선택
    print("\n1. Quick test (100 samples)")
    print("2. Medium training (1000 samples)")
    print("3. Full training (all samples)")
    print("4. Test existing model")
    
    choice = input("\nSelect (1/2/3/4): ").strip()
    
    if choice == '1':
        model = train_confusion_model(num_epochs=3, batch_size=4, max_samples=100)
        test_confusion_model(max_samples=50)
        
    elif choice == '2':
        model = train_confusion_model(num_epochs=5, batch_size=8, max_samples=1000)
        test_confusion_model(max_samples=200)
        
    elif choice == '3':
        model = train_confusion_model(num_epochs=10, batch_size=16, max_samples=None)
        test_confusion_model()
        
    elif choice == '4':
        if os.path.exists('confusion_binary_model.pth'):
            test_confusion_model()
        else:
            print("Error: No saved model found. Train first!")
    else:
        print("Invalid choice")