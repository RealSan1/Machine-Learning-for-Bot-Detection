import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy
import numpy as np

class Trainer:
    def __init__(self, model, criterion, optimizer, device='cuda' if torch.cuda.is_available() else 'cpu'):
        self.model = model.to(device)
        self.criterion = criterion
        self.optimizer = optimizer
        self.device = device
        
        self.train_losses = []
        self.valid_losses = []
        
    def train_one_epoch(self, x_train, y_train, batch_size):
        self.model.train()
        indices = torch.randperm(x_train.size(0), device=self.device)
        x_shuffled = x_train[indices]
        y_shuffled = y_train[indices]
        
        total_loss = 0.0
        for i in range(0, x_train.size(0), batch_size):
            x_batch = x_shuffled[i:i+batch_size].to(self.device)
            y_batch = y_shuffled[i:i+batch_size].to(self.device)
            
            self.optimizer.zero_grad()
            outputs = self.model(x_batch)
            loss = self.criterion(outputs, y_batch)
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item() * x_batch.size(0)
        return total_loss / x_train.size(0)
    
    def validate(self, x_valid, y_valid, batch_size):
        self.model.eval()
        total_loss = 0.0
        with torch.no_grad():
            for i in range(0, x_valid.size(0), batch_size):
                x_batch = x_valid[i:i+batch_size].to(self.device)
                y_batch = y_valid[i:i+batch_size].to(self.device)
                outputs = self.model(x_batch)
                loss = self.criterion(outputs, y_batch)
                total_loss += loss.item() * x_batch.size(0)
        return total_loss / x_valid.size(0)
    
    def fit(self, x_train, y_train, x_valid, y_valid,
            n_epochs=200, batch_size=128, early_stop_patience=10, print_every=10):
        
        best_loss = np.inf
        best_epoch = 0
        best_state_dict = None
        patience_counter = 0
        
        for epoch in range(n_epochs):
            train_loss = self.train_one_epoch(x_train, y_train, batch_size)
            valid_loss = self.validate(x_valid, y_valid, batch_size)
            
            self.train_losses.append(train_loss)
            self.valid_losses.append(valid_loss)
            
            if (epoch + 1) % print_every == 0:
                print(f"Epoch {epoch+1:3d}: train {train_loss:.4e} | valid {valid_loss:.4e} | best {best_loss:.4e}")
            
            # Early stopping & best model save
            if valid_loss < best_loss:
                best_loss = valid_loss
                best_epoch = epoch
                best_state_dict = deepcopy(self.model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= early_stop_patience:
                    print(f"Early stopping at epoch {epoch+1}")
                    break
        
        # 최적 모델 복원
        self.model.load_state_dict(best_state_dict)
        print(f"Best valid loss: {best_loss:.4e} at epoch {best_epoch+1}")
        
        return best_loss