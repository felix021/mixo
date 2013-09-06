mixo
====

A secured socks5 proxy over the Great Fucking Wall.

一点废话
--------

因为不满ssh tunnel的使用效果，所以2012年12月某天（大概是17号）心血来潮写了这个小东西，由于 [socks5协议](http://www.openssh.com/txt/rfc1928.txt) 本身很简单、加上gevent/greenlet使得异步开发跟同步似的，所以200行就搞定了。但是性能上问题很大——主要是加密有问题。尽管加密就是最简单的xor，但是因为python不适合处理大量的小对象，所以当时写了一个python扩展，性能上就没问题了，但是又多了一项麻烦的依赖。后来发现已经有更成熟的shadowsocks，于是就弃坑了，也一直没有发布。

今天[2013.08.16]心血来潮，用ctypes来实现同样的功能，似乎也挺合适的；不过跟shadowsocks比起来有两个地方做得不好，一是没有更“高级”的加密方式（他家用了M2Crypto，代码看起来很复杂），另一个是shadowsocks在本地先回应socks5请求，只把必要的host:port信息发送给server，减少了一个来回，而我原先的实现则是在server端实现完整的socks5(现在把step1搬到client了，因为改动很小)。

总之好歹也是个凑合能用的东西了，发布出来晾着吧，也许哪天有人就用上了呢。

依赖
--------

1. Python 2.6/2.7
2. greenlet: http://pypi.python.org/pypi/greenlet
3. gevent: https://pypi.python.org/pypi/gevent

前面提到的c库，mixo自带了4个版本的so文件:

1. xor\_ELF\_32bit.so: linux/32bit
2. xor\_ELF\_64bit.so: linux/64bit
3. xor\_WindowsPE\_32bit.so: windows/32bit
4. xor\_WindowsPE\_64bit.so: windows/64bit #未测试:(

如果觉得不放心，可以自己编译：

    $ make

使用
--------

1. 修改配置：config.py
    
    其中seed是密钥，改成任意整数；其他ip、端口什么的根据实际需要填吧。

2. 启动Server:
    
    $ python server.py

3. 启动Client:

    $ python client.py
