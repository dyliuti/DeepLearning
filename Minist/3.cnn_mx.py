import mxnet as mx
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from keras.utils.np_utils import to_categorical
from sklearn.metrics import confusion_matrix
from Data.DataPlot import plot_acc_loss_ke, plot_confusion_matrix


# Epoch[99] Train-accuracy=0.988835
# Epoch[99] Time cost=2.509
# Epoch[99] Validation-accuracy=0.994257

# logging.basicConfig(format='%(message)s', level=logging.INFO)
##### 数据读取 #####
train = pd.read_csv('Data/Minist/train.csv')
Y_train = train['label']
X_train = train.drop(labels=['label'], axis=1)

# 标准化
X_train = X_train / 255.0
# 区别mx： N, 1, 28, 28  keras: N, 28, 28, 1
X_train = X_train.values.reshape(-1, 1, 28,28)
# 目标one-hot编码
Y_train = to_categorical(Y_train, num_classes = 10)
# 训练集中分训练与验证两部分
random_seed = 2
X_train, X_test, Y_train, Y_test = train_test_split(X_train, Y_train, test_size = 0.1, random_state=random_seed)


##### 构建模型 #####
data = mx.sym.Variable('data')
# pad区别，keras用字符，mxnet需要自已计算
conv1_1 = mx.sym.Convolution(data=data, kernel=(3,3), pad=(1,1), num_filter=32, name='conv1_1')
relu1_1 = mx.sym.Activation(data=conv1_1, act_type='relu', name='relu1_1')
conv1_2 = mx.sym.Convolution(data=relu1_1, kernel=(3,3), pad=(1,1), num_filter=32, name='conv1_2')
relu1_2 = mx.sym.Activation(data=conv1_2, act_type='relu', name='relu1_2')
# pool区别，keras用函数，mxnet函数接口少了，用字符 pool_size <-> kernel
pool1 = mx.sym.Pooling(data=relu1_2, kernel=(2,2), pool_type='max', stride=(2,2), pad=(0,0), name='pool1') #
drop1 = mx.sym.Dropout(data=pool1, p=0.25, name='drop1')

conv2_1 = mx.sym.Convolution(data=drop1, kernel=(3,3), pad=(1,1), num_filter=64, name='conv2_1')
relu2_1 = mx.sym.Activation(data=conv2_1, act_type='relu', name='relu2_1')
conv2_2 = mx.sym.Convolution(data=relu2_1, kernel=(3,3), pad=(1,1), num_filter=64, name='conv2_2')
relu2_2 = mx.sym.Activation(data=conv2_2, act_type='relu', name='relu2_2')
# pool区别，keras用函数，mxnet函数接口少了，用字符 pool_size <-> kernel
pool2 = mx.sym.Pooling(data=relu2_2, kernel=(2,2), pool_type='max', stride=(2,2), pad=(0,0), name='pool2')
drop2 = mx.sym.Dropout(data=pool2, p=0.25, name='drop2')

flat = mx.sym.Flatten(data=drop2, name='flat')
fcn1 = mx.sym.FullyConnected(data=flat, num_hidden=256, name='fcn1')
relu3 = mx.sym.Activation(data=fcn1, act_type='relu', name='relu3')
drop3 = mx.sym.Dropout(data=relu3, p=0.5, name='drop3')
fcn2 = mx.sym.FullyConnected(data=drop3, num_hidden=10, name='fcn2')
sym = mx.sym.SoftmaxOutput(data=fcn2, name='softmax')
print(sym.list_arguments())
# 区别mx：NCHW N, 1, 28, 28  keras: N, 28, 28, 1
# print(sym.infer_shape(data=(86, 1, 28, 28)))

##### 训练模型 ######
epochs = 100
batch_size = 86
train_iter = mx.io.NDArrayIter(data={'data': X_train},
							   label={'softmax_label': Y_train},
							   batch_size=batch_size,
							   shuffle=True)
val_iter = mx.io.NDArrayIter(data={'data': X_test},
							 label={'softmax_label': Y_test},
							 batch_size=batch_size)
print(train_iter.provide_data)
print(train_iter.provide_label)
model = mx.mod.Module(symbol=sym, context=mx.gpu())
print(X_train.shape)
# epoch_size = max(int( / batch_size), 1)

lr_scheduler = mx.lr_scheduler.MultiFactorScheduler(step=[70], factor=0.1)
optimizer_params = {'learning_rate': 0.0005,
					'lr_scheduler': lr_scheduler}  # 学习率变化策略
initializer = mx.init.Xavier(rnd_type='gaussian', factor_type="in", magnitude=2)
model.fit(train_data=train_iter,
		  eval_data=val_iter,
		  eval_metric=['acc'], # , 'loss'
		  optimizer='adam',
		  optimizer_params={'learning_rate':0.0005},
		  # optimizer_params=optimizer_params, # {'learning_rate':0.0005},
		  initializer=initializer,
		  num_epoch=epochs)
# print(model.get_outputs())

##### 预测 #####
val_iter.reset()
Y_preds = []
Y_trues = []
for batch in val_iter:
	# batch = val_iter.next()
	data = batch.data[0]
	Y_true = batch.label[0].asnumpy().astype(dtype=np.int32).tolist()
	# 预测返回的是NDArray
	Y_pred = model.predict(data).asnumpy().tolist()
	# 将预测结果转换为索引
	Y_true = np.argmax(Y_true, axis=1)
	Y_pred_classes = np.argmax(Y_pred, axis = 1)
	Y_preds.extend(Y_pred_classes)		# 用 np.append(a, b)也可以
	Y_trues.extend(Y_true)
# 计算并绘制混淆矩阵
confusion_mtx = confusion_matrix(Y_trues, Y_preds)
plot_confusion_matrix(confusion_mtx, classes = range(10))
