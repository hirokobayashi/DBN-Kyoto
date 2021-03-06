from __future__ import print_function, division
import os
import sys
import timeit

import numpy

from theano.tensor.shared_randomstreams import RandomStreams

import dbn as deep
import pandas as pd

def main(finetune_lr=0.1, pretraining_epochs=0,
             pretrain_lr=0.01, k=1, training_epochs=100,
             dataset='cpi.npz', batch_size=10,
             hidden_layers_sizes=[2000,2000,2000]):

    datasets = deep.load_data(dataset)

    train_set_x, train_set_y = datasets[0]
    test_set_x, test_set_y = datasets[1]

    n_in = train_set_x.shape[1].eval()
    n_out = len(set(train_set_y.eval()))

    # compute number of minibatches for training and testing
    n_train_batches = train_set_x.get_value(borrow=True).shape[0] // batch_size

    # numpy random generator
    numpy_rng = numpy.random.RandomState(123)
    print('... building the model')
    # construct the Deep Belief Network
    dbn = deep.DBN(numpy_rng=numpy_rng, n_ins=n_in,
              hidden_layers_sizes=hidden_layers_sizes,
              n_outs=n_out)

    # start-snippet-2
    #########################
    # PRETRAINING THE MODEL #
    #########################
    print('... getting the pretraining functions')
    pretraining_fns = dbn.pretraining_functions(train_set_x=train_set_x,
                                                batch_size=batch_size,
                                                k=k)

    print('... pre-training the model')
    start_time = timeit.default_timer()
    # Pre-train layer-wise
    for i in range(dbn.n_layers):
        # go through pretraining epochs
        for epoch in range(pretraining_epochs):
            # go through the training set
            c = []
            for batch_index in range(n_train_batches):
                c.append(pretraining_fns[i](index=batch_index,
                                            lr=pretrain_lr))
            print('Pre-training layer %i, epoch %d, cost ' % (i, epoch), end=' ')
            print(numpy.mean(c, dtype='float64'))

    end_time = timeit.default_timer()
    # end-snippet-2
    print('The pretraining code for file ' + os.path.split(__file__)[1] +
          ' ran for %.2fm' % ((end_time - start_time) / 60.), file=sys.stderr)
    ########################
    # FINETUNING THE MODEL #
    ########################

    # get the training and testing function for the model
    print('... getting the finetuning functions')
    train_fn, test_model = deep.build_finetune_functions(dbn,
        datasets=datasets,
        batch_size=batch_size,
        learning_rate=finetune_lr
    )

    print('... finetuning the model')
    # early-stopping parameters

    # look as this many examples regardless
    patience = 4 * n_train_batches

    # wait this much longer when a new best is found
    patience_increase = 2.

    # a relative improvement of this much is considered significant
    improvement_threshold = 0.995

    # go through this many minibatches before checking the network on
    # the test set; in this case we check every epoch
    test_frequency = min(n_train_batches, patience / 2)

    # Jason changed, pcs, make the test_freq higher is good for performance, especially when the dataset is large.
    test_frequency = n_train_batches

    best_test_loss = numpy.inf
    test_score = 0.
    start_time = timeit.default_timer()

    done_looping = False
    epoch = 0

    score = []
    batch_range = numpy.arange(n_train_batches)
    while (epoch < training_epochs) and (not done_looping):
        epoch = epoch + 1
        numpy.random.shuffle(batch_range)
        for minibatch_index in range(n_train_batches):

            minibatch_avg_cost = train_fn(batch_range[minibatch_index])
            iter = (epoch - 1) * n_train_batches + minibatch_index

            if (iter + 1) % test_frequency == 0:

                test_losses = test_model()
                this_test_loss = numpy.mean(test_losses, dtype='float64')
                score.append([epoch,this_test_loss])
                print('epoch %i, minibatch %i/%i, test error %f %%' % (
                    epoch,
                    minibatch_index + 1,
                    n_train_batches,
                    this_test_loss * 100.
                    )
                )

                # if we got the best test score until now
                if this_test_loss < best_test_loss:

                    # improve patience if loss improvement is good enough
                    if (this_test_loss < best_test_loss *
                            improvement_threshold):
                        patience = max(patience, iter * patience_increase)

                    # save best test score and iteration number
                    best_test_loss = this_test_loss
                    best_iter = iter

            if patience <= iter:
                pass

    end_time = timeit.default_timer()
    print(('Optimization complete with best test score of %f %%, '
           'obtained at iteration %i, '
           'with test performance %f %%'
           ) % (best_test_loss * 100., best_iter + 1, test_score * 100.))
    print('The fine tuning code for file ' + os.path.split(__file__)[1] +
          ' ran for %.2fm' % ((end_time - start_time) / 60.), file=sys.stderr)

    if not os.path.exists('result'):
        os.makedirs('result')

    df = pd.DataFrame(score)
    df.to_pickle('result/%s_%dx%d.log' % (os.path.basename(dataset),
        hidden_layers_sizes[0], len(hidden_layers_sizes)))

if __name__ == '__main__':
    if len(sys.argv) > 1:
        dataset = sys.argv[1]
    else:
        sys.exit('Usage: %s [datafile]' % sys.argv[0])

    hidden_layers_sizes=[2000,2000,2000]
    batch_size = 10
    print(hidden_layers_sizes[0], len(hidden_layers_sizes), batch_size)
    main(dataset=dataset, hidden_layers_sizes=hidden_layers_sizes)
