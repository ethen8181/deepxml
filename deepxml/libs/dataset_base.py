import torch
import _pickle as pickle
import os
import sys
from scipy.sparse import lil_matrix
import numpy as np
from sklearn.preprocessing import normalize
import xclib.data.data_utils as data_utils
import operator
from .lookup import Table, PartitionedTable
from .features import construct as construct_f
from .labels import construct as construct_l


class DatasetBase(torch.utils.data.Dataset):
    """
        Dataset to load and use XML-Datasets
    """

    def __init__(self, data_dir, fname_features, fname_labels, data=None, model_dir='', 
                mode='train', feature_indices=None, label_indices=None, keep_invalid=False, 
                 normalize_features=True, normalize_lables=False, feature_type='sparse', label_type='dense'):
        """
            Support pickle or libsvm file format
            Args:
                data_file: str: File name for the set
        """
        self.data_dir = data_dir
        self.mode = mode
        self.features, self.labels, self.num_samples, \
            self.num_features, self.num_labels = self.load_data(
                data_dir, fname_features, fname_labels, data, normalize_features, 
                normalize_lables, feature_type, label_type)
        self._split = None
        self.index_select(feature_indices, label_indices)
        self.model_dir = model_dir
        self.data_dir = data_dir
        self.label_padding_index = self.num_labels

    def _remove_samples_wo_features_and_labels(self):
        """
            Remove instances if they don't have any feature or label
        """
        indices_feat = self.features.get_valid(axis=1)
        indices_labels = self.labels.get_valid(axis=1)
        indices = np.intersect1d(indices_feat, indices_labels)
        self.features.index_select(indices, axis=0)
        self.labels.index_select(indices, axis=0)
        self.update_data_stats()

    def index_select(self, feature_indices, label_indices):
        def _get_split_id(fname):
            idx = fname.split("_")[-1].split(".")[0]
            return idx
        if label_indices is not None:
            self._split = _get_split_id(label_indices)
            label_indices = np.loadtxt(label_indices, dtype=np.int32)
            self.labels.index_select(label_indices, axis=1)
        if feature_indices is not None:
            self._split = _get_split_id(feature_indices)
            feature_indices = np.loadtxt(feature_indices, dtype=np.int32)
            self.features.index_select(feature_indices, axis=1)
        self.update_data_stats()

    def update_data_stats(self):
        """
            Update num_samples, num_features, num_labels
        """
        self.num_samples = self.features.num_instances
        self.num_features = self.features.num_features
        self.num_labels = self.labels.num_labels

    def _sel_labels(self, label_indices):
        """
            Train only for given labels
        """
        def _get_split_id(fname):
            idx = fname.split("_")[-1].split(".")[0]
            return idx
        if label_indices is not None:
            self._split = _get_split_id(label_indices)
            label_indices = np.loadtxt(label_indices, dtype=np.int32)
            self.labels = self.labels[:, label_indices]
            self.num_labels = self.labels.shape[1]

    def load_data(self, data_dir, fname_f, fname_l, data, 
                  normalize_features=True, normalize_labels=False,
                  feature_type='sparse', label_type='dense'):
        """
            Load features and labels from file in libsvm format or pickle
        """
        features = construct_f(data_dir, fname_f, data['X'], normalize_features, feature_type)
        labels = construct_l(data_dir, fname_l, data['Y'], normalize_labels, label_type) # Pass dummy labels if required
        if normalize_labels:
            if self.mode == 'train': # Handle non-binary labels
                print("Non-binary labels encountered in train; Normalizing...")
                labels.normalize(norm='max', copy=False)
            else:
                print("Non-binary labels encountered in test/val; Binarizing...")
                labels.binarize()
        assert features.num_instances == labels.num_instances
        num_samples = features.num_instances
        num_features = features.num_features
        num_labels = labels.num_labels
        return features, labels, num_samples, num_features, num_labels

    def get_stats(self):
        """
            Get dataset statistics
        """
        return self.num_samples, self.num_features, self.num_labels

    def _process_labels_train(self, data_obj):
        """
            Process labels for train data
            - Remove labels without any training instance
            - Handle multiple centroids
        """
        valid_labels = self.labels.remove_invalid()
        data_obj['valid_labels'] = valid_labels
        data_obj['num_labels'] = self.num_labels
        self.update_data_stats()
        
    def _process_labels_predict(self, data_obj):
        """
            Process labels for re-train data
            - Remove labels without any training instance
            - Handle multiple centroids
        """
        valid_labels = data_obj['valid_labels']
        self.labels.index_select(valid_labels)
        self.update_data_stats()

    def _process_labels(self, model_dir):
        """
            Process labels to handle labels without any training instance;
            Handle multiple centroids if required
        """
        data_obj = {}
        fname = os.path.join(
            model_dir, 'labels_params.pkl' if self._split is None else \
                "labels_params_split_{}.pkl".format(self._split))
        if self.mode == 'train':
            self._process_labels_train(data_obj)
            pickle.dump(data_obj, open(fname, 'wb'))
        else:
            data_obj = pickle.load(open(fname, 'rb'))
            self._process_labels_predict(data_obj)

    def __len__(self):
        return self.num_samples

    def __getitem__(self, index):
        """
            Get features and labels for index
            Args:
                index: for this sample
            Returns:
                features: : non zero entries
                labels: : numpy array

        """
        x = self.features[index]
        y = self.labels[index]
        return x, y
