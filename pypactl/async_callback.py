import asyncio

def async_callback(loop, func, *args, **kwargs):
    future = loop.create_future()
    def callback_proxy(result=None):
        future.set_result(result)
    kwargs['callback'] = callback_proxy
    func(*args, **kwargs)
    return future
