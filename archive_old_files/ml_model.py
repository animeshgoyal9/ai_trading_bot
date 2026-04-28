"""
Machine Learning Model Module
Trains and predicts stock price movements
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from xgboost import XGBClassifier
import joblib
from datetime import datetime
from loguru import logger
import config


class TradingModel:
    """Machine Learning model for trading predictions"""

    def __init__(self, model_type='xgboost'):
        self.model_type = model_type
        self.model = None
        self.feature_importance = None
        self.metrics = {}

    def build_model(self):
        """Build the ML model based on configuration"""
        if self.model_type == 'xgboost':
            self.model = XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                eval_metric='logloss'
            )
        elif self.model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == 'gradient_boosting':
            self.model = GradientBoostingClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                random_state=42
            )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

        logger.info(f"Built {self.model_type} model")

    def train(self, X_train, y_train, X_val=None, y_val=None):
        """
        Train the model

        Args:
            X_train: Training features
            y_train: Training target
            X_val: Validation features (optional)
            y_val: Validation target (optional)
        """
        if self.model is None:
            self.build_model()

        logger.info(f"Training {self.model_type} model with {len(X_train)} samples")

        # Train the model
        if self.model_type == 'xgboost' and X_val is not None:
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False
            )
        else:
            self.model.fit(X_train, y_train)

        # Calculate feature importance
        if hasattr(self.model, 'feature_importances_'):
            self.feature_importance = pd.DataFrame({
                'feature': X_train.columns,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)

            logger.info(f"Top 10 features:\n{self.feature_importance.head(10)}")

        logger.info("Model training completed")

    def predict(self, X):
        """
        Make predictions

        Returns:
            Array of predictions (0 or 1)
        """
        if self.model is None:
            raise ValueError("Model not trained yet")

        return self.model.predict(X)

    def predict_proba(self, X):
        """
        Predict probabilities

        Returns:
            Array of probabilities for each class
        """
        if self.model is None:
            raise ValueError("Model not trained yet")

        return self.model.predict_proba(X)

    def evaluate(self, X_test, y_test):
        """
        Evaluate model performance

        Returns:
            Dictionary of metrics
        """
        y_pred = self.predict(X_test)
        y_proba = self.predict_proba(X_test)[:, 1]

        self.metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1_score': f1_score(y_test, y_pred, zero_division=0),
        }

        logger.info(f"Model Performance:")
        logger.info(f"  Accuracy:  {self.metrics['accuracy']:.4f}")
        logger.info(f"  Precision: {self.metrics['precision']:.4f}")
        logger.info(f"  Recall:    {self.metrics['recall']:.4f}")
        logger.info(f"  F1 Score:  {self.metrics['f1_score']:.4f}")

        logger.info(f"\nClassification Report:\n{classification_report(y_test, y_pred)}")

        return self.metrics

    def save_model(self, filepath='models'):
        """Save trained model to disk"""
        import os
        os.makedirs(filepath, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{filepath}/{self.model_type}_model_{timestamp}.joblib"

        joblib.dump(self.model, filename)
        logger.info(f"Model saved to {filename}")

        # Save feature importance
        if self.feature_importance is not None:
            importance_file = f"{filepath}/{self.model_type}_feature_importance_{timestamp}.csv"
            self.feature_importance.to_csv(importance_file, index=False)

        return filename

    def load_model(self, filepath):
        """Load trained model from disk"""
        self.model = joblib.load(filepath)
        logger.info(f"Model loaded from {filepath}")

    def cross_validate(self, X, y, n_splits=5):
        """
        Perform time series cross-validation

        Returns:
            Dictionary of average metrics
        """
        tscv = TimeSeriesSplit(n_splits=n_splits)
        scores = {
            'accuracy': [],
            'precision': [],
            'recall': [],
            'f1': []
        }

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            logger.info(f"Cross-validation fold {fold + 1}/{n_splits}")

            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            # Build and train model
            self.build_model()
            self.train(X_train, y_train)

            # Evaluate
            y_pred = self.predict(X_val)

            scores['accuracy'].append(accuracy_score(y_val, y_pred))
            scores['precision'].append(precision_score(y_val, y_pred, zero_division=0))
            scores['recall'].append(recall_score(y_val, y_pred, zero_division=0))
            scores['f1'].append(f1_score(y_val, y_pred, zero_division=0))

        # Calculate averages
        avg_scores = {metric: np.mean(values) for metric, values in scores.items()}

        logger.info("Cross-validation results:")
        for metric, score in avg_scores.items():
            logger.info(f"  {metric}: {score:.4f} (+/- {np.std(scores[metric]):.4f})")

        return avg_scores


def prepare_train_test_data(df, feature_cols, target_col='target'):
    """
    Prepare train and test datasets

    Args:
        df: DataFrame with features and target
        feature_cols: List of feature column names
        target_col: Name of target column

    Returns:
        X_train, X_test, y_train, y_test
    """
    # Remove rows with NaN in target
    df = df.dropna(subset=[target_col])

    # Split features and target
    X = df[feature_cols]
    y = df[target_col]

    # Time series split (preserve order)
    split_idx = int(len(df) * config.TRAIN_TEST_SPLIT)

    X_train = X.iloc[:split_idx]
    X_test = X.iloc[split_idx:]
    y_train = y.iloc[:split_idx]
    y_test = y.iloc[split_idx:]

    logger.info(f"Train set: {len(X_train)} samples, Test set: {len(X_test)} samples")
    logger.info(f"Train positive ratio: {y_train.mean():.2%}")
    logger.info(f"Test positive ratio: {y_test.mean():.2%}")

    return X_train, X_test, y_train, y_test
