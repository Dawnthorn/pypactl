import asyncio

def async_callback(loop, func, **args):
    print(f"async_callback({func})")
    future = loop.create_future()
    def callback_proxy(result=None):
        print(f"callback_proxy({func})")
        future.set_result(result)
    args['callback'] = callback_proxy
    func(**args)
    return future
