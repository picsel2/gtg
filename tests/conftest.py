from GTG import gi_version_requires

def pytest_collection(session):
    gi_version_requires()

