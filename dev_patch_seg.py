import argparse

import wandb
import numpy as np
import tensorflow_addons as tfa
from sklearn.model_selection import train_test_split
from wandb.integration.keras import WandbCallback

from model.vit_keras import vit
import tensorflow as tf

# def get_position_embeddings(model):
#     pos = tf.keras.Model(model.input, model.layers[1].output)
#     patch = np.zeros((1, 10, pow(window_size,2)*5))
#     positional_embeddings = pos.predict(patch)
#     num_patches=10
#     output_heatmap = np.zeros((num_patches, num_patches))
#
#     output_heatmap = cosine_similarity(positional_embeddings, positional_embeddings)
#
#     fig, ax = plt.subplots()
#     im = plt.imshow(output_heatmap)
#     # Show all ticks and label them with the respective list entries
#     plt.xticks(np.arange(num_patches))
#     plt.yticks(np.arange(num_patches))
#
#     # Rotate the tick labels and set their alignment.
#     plt.setp(ax.get_xticklabels(), rotation=45, ha="right",
#              rotation_mode="anchor")
#
#     # Loop over data dimensions and create text annotations.
#     for i in range(num_patches):
#         for j in range(num_patches):
#             text = plt.text(j, i, np.around(output_heatmap[i, j], decimals=2),
#                             ha="center", va="center", color="w")
#     plt.colorbar()
#     plt.title('Positional embedding Similarity')
#     plt.xlabel('Sequence number')
#     plt.ylabel('Sequence number')
#     fig.tight_layout()
#     plt.show()
if __name__=='__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-w', type=int, help='Window size')
    parser.add_argument('-p', type=str, help='Pretrained')



    args = parser.parse_args()
    load_pretrained = args.p
    window_size = args.w
    model_name='patch_seg'
    batch_size=256
    MAX_EPOCHS = 50
    learning_rate = 0.001
    weight_decay = 0.0001

    num_classes=2
    input_shape=(10,pow(window_size,2)*5)

    x_dataset = np.load('/NOBACKUP/zhao2/proj3_train_w'+str(window_size)+'patch_seg.npy')
    y_dataset = np.load('/NOBACKUP/zhao2/proj3_train_w'+str(window_size)+'label.npy')>0

    x_train, x_val, y_train, y_val = train_test_split(x_dataset[:,:,:pow(window_size,2)*5], y_dataset, test_size=0.2)
    print(x_train.shape)
    print(y_train.shape)

    def make_generator(inputs, labels):
        def _generator():
            for input, label in zip(inputs, labels):
                yield input, label

        return _generator


    train_dataset = tf.data.Dataset.from_generator(make_generator(x_train, y_train),
                                             (tf.float32, tf.int16))
    val_dataset = tf.data.Dataset.from_generator(make_generator(x_val, y_val),
                                             (tf.float32, tf.int16))

    train_dataset = train_dataset.shuffle(batch_size).repeat(MAX_EPOCHS).batch(batch_size)
    val_dataset = val_dataset.shuffle(batch_size).repeat(MAX_EPOCHS).batch(batch_size)





    wandb.login()
    wandb.init(project="tokenized_window_size"+ str(window_size) +str(model_name), entity="zhaoyutim")
    # wandb.config = {
    #   "learning_rate": learning_rate,
    #   "weight_decay": weight_decay,
    #   "epochs": MAX_EPOCHS,
    #   "batch_size": batch_size,
    #   "num_heads":num_heads,
    #   "transformer_layers": transformer_layers
    # }
    strategy = tf.distribute.MirroredStrategy()
    with strategy.scope():
        model = vit.vit_small_patch_segment(
            input_shape=input_shape,
            activation='sigmoid',
            pretrained=True,
            include_top=True,
            pretrained_top=True
        )

        model.summary()

        optimizer = tfa.optimizers.AdamW(
            learning_rate=learning_rate, weight_decay=weight_decay
        )

        model.compile(
            optimizer=optimizer,
            loss=tf.keras.losses.BinaryCrossentropy(from_logits=False),
            metrics=[
                tf.keras.metrics.BinaryAccuracy(name="accuracy")
            ],
        )

    options = tf.data.Options()
    options.experimental_distribute.auto_shard_policy = tf.data.experimental.AutoShardPolicy.OFF
    train_dataset = train_dataset.with_options(options)
    val_dataset = val_dataset.with_options(options)

    if load_pretrained=='yes':
        model.load_weights('/NOBACKUP/zhao2/proj3_' + model_name + 'w' + str(window_size) + '_nopretrained_patch_seg')
    else:
        print('training in progress')
        history = model.fit(
            x=train_dataset,
            batch_size=batch_size,
            steps_per_epoch=x_train.shape[0]//batch_size,
            validation_data=val_dataset,
            validation_steps=x_val.shape[0]//batch_size,
            epochs=MAX_EPOCHS,
            callbacks=[WandbCallback()],
        )
        model.save('/NOBACKUP/zhao2/proj3_'+model_name+'w' + str(window_size) + '_nopretrained_patch_seg')
