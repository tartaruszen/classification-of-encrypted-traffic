import numpy as np
from tensorflow.python.framework import dtypes
from tensorflow.python.framework import random_seed
from tensorflow.contrib.learn.python.learn.datasets import base
import glob
import os
import utils
import pandas as pd
from sklearn.preprocessing import LabelEncoder

_label_encoder = LabelEncoder()


class DataSet(object):

    def __init__(self,
                 payloads,
                 labels,
                 dtype=dtypes.float32,
                 seed=None):
        """Construct a DataSet.
        one_hot arg is used only if fake_data is true.  `dtype` can be either
        `uint8` to leave the input as `[0, 255]`, or `float32` to rescale into
        `[0, 1]`.  Seed arg provides for convenient deterministic testing.
        """
        seed1, seed2 = random_seed.get_seed(seed)
        # If op level seed is not set, use whatever graph level seed is returned
        np.random.seed(seed1 if seed is None else seed2)
        dtype = dtypes.as_dtype(dtype).base_dtype
        if dtype not in (dtypes.uint8, dtypes.float32):
            raise TypeError('Invalid payload dtype %r, expected uint8 or float32' %
                            dtype)

        assert payloads.shape[0] == labels.shape[0], (
                'payloads.shape: %s labels.shape: %s' % (payloads.shape, labels.shape))
        self._num_examples = payloads.shape[0]

        if dtype == dtypes.float32:
            # Convert from [0, 255] -> [0.0, 1.0].
            payloads = payloads.astype(np.float32)
            payloads = np.multiply(payloads, 1.0 / 255.0)

        self._payloads = payloads
        self._labels = labels
        self._epochs_completed = 0
        self._index_in_epoch = 0

    @property
    def payloads(self):
        return self._payloads

    @property
    def labels(self):
        return self._labels

    @property
    def num_examples(self):
        return self._num_examples

    @property
    def epochs_completed(self):
        return self._epochs_completed

    def next_batch(self, batch_size, shuffle=True):
        """Return the next `batch_size` examples from this data set."""
        start = self._index_in_epoch
        # Shuffle for the first epoch

        if self._epochs_completed == 0 and start == 0 and shuffle:
            perm0 = np.arange(self._num_examples)
            np.random.shuffle(perm0)
            self._payloads = self.payloads[perm0]
            self._labels = self.labels[perm0]
        # Go to the next epoch
        if start + batch_size > self._num_examples:
            # Finished epoch
            self._epochs_completed += 1
            # Get the rest examples in this epoch
            rest_num_examples = self._num_examples - start
            payloads_rest_part = self._payloads[start:self._num_examples]
            labels_rest_part = self._labels[start:self._num_examples]
            # Shuffle the data
            if shuffle:
                perm = np.arange(self._num_examples)
                np.random.shuffle(perm)
                self._payloads = self.payloads[perm]
                self._labels = self.labels[perm]
            # Start next epoch
            start = 0
            self._index_in_epoch = batch_size - rest_num_examples
            end = self._index_in_epoch
            images_new_part = self._payloads[start:end]
            labels_new_part = self._labels[start:end]
            return np.concatenate((payloads_rest_part, images_new_part), axis=0), np.concatenate(
                (labels_rest_part, labels_new_part), axis=0)
        else:
            self._index_in_epoch += batch_size
            end = self._index_in_epoch
            return self._payloads[start:end], self._labels[start:end]


def dense_to_one_hot(labels_dense, num_classes):
    """Convert class labels from scalars to one-hot vectors."""
    num_labels = labels_dense.shape[0]
    index_offset = np.arange(num_labels) * num_classes
    labels_one_hot = np.zeros((num_labels, num_classes), dtype=np.int8)
    labels_one_hot.flat[index_offset + labels_dense.ravel()] = 1
    return labels_one_hot


def extract_labels(dataframe, one_hot=False, num_classes=10):
    """Extract the labels into a 1D uint8 numpy array [index].

    Args:
    dataframe: A pandas dataframe object.
    one_hot: Does one hot encoding for the result.
    num_classes: Number of classes for the one hot encoding.

    Returns:
    labels: a 1D uint8 numpy array.
    """
    print('Extracting labels', )
    labels = dataframe['label'].values
    labels = _label_encoder.fit_transform(labels)
    if one_hot:
        return dense_to_one_hot(labels, num_classes)
    return labels


def read_data_sets(train_dirs=[], test_dirs=None,
                   merge_data=True,
                   one_hot=False,
                   dtype=dtypes.float32,
                   validation_size=0.2,
                   test_size=0.2,
                   seed=None,
                   balance_classes=False,
                   payload_length=810):
    trainframes = []
    testframes = []
    for train_dir in train_dirs:
        for fullname in glob.iglob(train_dir + '*.h5'):
            filename = os.path.basename(fullname)
            df = utils.load_h5(train_dir, filename)
            trainframes.append(df)
        # create one large dataframe
    train_data = pd.concat(trainframes)
    if test_dirs != train_dirs:
        for test_dir in test_dirs:
            for fullname in glob.iglob(test_dir + '*.h5'):
                filename = os.path.basename(fullname)
                df = utils.load_h5(test_dir, filename)
                testframes.append(df)
        test_data = pd.concat(testframes)
    else:
        test_data = pd.DataFrame()

    if merge_data:
        train_data = pd.concat([test_data, train_data])

    num_classes = len(train_data['label'].unique())

    if balance_classes:
        values, counts = np.unique(train_data['label'], return_counts=True)
        smallest_class = np.argmin(counts)
        amount = counts[smallest_class]
        new_data = []
        for v in values:
            sample = train_data.loc[train_data['label'] == v].sample(n=amount)
            new_data.append(sample)
        train_data = new_data
        train_data = pd.concat(train_data)


    # shuffle the dataframe and reset the index
    train_data = train_data.sample(frac=1, random_state=seed).reset_index(drop=True)
    #
    # youtube_selector = train_data['label'] == 'youtube'
    # youtube_data = train_data[youtube_selector]
    # for index, row in youtube_data.iterrows():
    #     bytes = row[0]
    #     if bytes[23] == 17.0:
    #         train_data.loc[index, 'label'] = 'youtube_udp'
    #     else:
    #         train_data.loc[index, 'label'] = 'youtube_tcp'

    if test_dirs != train_dirs:
        test_data = test_data.sample(frac=1, random_state=seed).reset_index(drop=True)
        test_labels = extract_labels(test_data, one_hot=one_hot, num_classes=num_classes)
        test_payloads = test_data['bytes'].values
        test_payloads = utils.pad_arrays_with_zero(test_payloads, payload_length=payload_length)
    train_labels = extract_labels(train_data, one_hot=one_hot, num_classes=num_classes)
    train_payloads = train_data['bytes'].values
    # pad with zero up to payload_length length
    train_payloads = utils.pad_arrays_with_zero(train_payloads, payload_length=payload_length)

    # TODO make seperate TEST SET ONCE ready
    total_length = len(train_payloads)
    validation_amount = int(total_length * validation_size)
    if merge_data:
        test_amount = int(total_length * test_size)
        test_payloads = train_payloads[:test_amount]
        test_labels = train_labels[:test_amount]
        val_payloads = train_payloads[test_amount:(validation_amount + test_amount)]
        val_labels = train_labels[test_amount:(validation_amount + test_amount)]
        train_payloads = train_payloads[(validation_amount + test_amount):]
        train_labels = train_labels[(validation_amount + test_amount):]
    else:
        val_payloads = train_payloads[:validation_amount]
        val_labels = train_labels[:validation_amount]
        train_payloads = train_payloads[validation_amount:]
        train_labels = train_labels[validation_amount:]

    options = dict(dtype=dtype, seed=seed)
    print("Training set size: {0}".format(len(train_payloads)))
    print("Validation set size: {0}".format(len(val_payloads)))
    print("Test set size: {0}".format(len(test_payloads)))
    train = DataSet(train_payloads, train_labels, **options)
    validation = DataSet(val_payloads, val_labels, **options)
    test = DataSet(test_payloads, test_labels, **options)

    return base.Datasets(train=train, validation=validation, test=test)
