import pkg_resources


def load_plugins(namespace: str) -> dict:
    res = dict()
    for ep in pkg_resources.iter_entry_points(group=namespace):
        try:
            res[ep.name] = ep.load(require=True)
        except ImportError as ie:
            print("Plugin %r import failed: %s" % (ep, ie))
        except pkg_resources.UnknownExtra as ue:
            print("Plugin %r dependencies resolution failed: %s" % (ep, ue))
        else:
            print(" Plugin %s ready" % ep.name)
    return res
