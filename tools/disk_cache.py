import hashlib
import os
import pickle


def disk_cache(active_fn=lambda: True, cache_dir='./_cache'):
    def disk_cache_decorator(fn):
        fn_cache_dir = os.path.join(cache_dir, ''.join(c for c in fn.__name__ if c not in '\0./?'))

        def mk_cache_dirs():
            for dirname in [cache_dir, fn_cache_dir]:
                try:
                    os.mkdir(dirname)
                except:
                    pass

        def wrapper(*args, **kwargs):
            if not active_fn():
                return fn(*args, **kwargs)
            slug = hashlib.md5(pickle.dumps((args, kwargs))).hexdigest()
            fname = os.path.join(fn_cache_dir, slug + '.pickle')
            if os.path.exists(fname):
                with open(fname) as f:
                    return pickle.load(f)
            else:
                mk_cache_dirs()
                value = fn(*args, **kwargs)
                try:
                    with open(fname, 'w') as f:
                        pickle.dump(value, f)
                    return value
                except:
                    try:
                        os.remove(fname)
                    except:
                        pass
                    raise
        return wrapper
    return disk_cache_decorator
