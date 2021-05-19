from setuptools import setup, find_packages

setup(name='push2-python',
      version='0.4',
      description='Utils to interface with Ableton\'s Push 2 from Python',
      url='https://github.com/ffont/push2-python',
      author='Frederic Font',
      author_email='frederic.font@gmail.com',
      license='MIT',
      install_requires=['numpy', 'pyusb', 'python-rtmidi', 'mido', 'flask', 'flask-socketio', 'evenlet'],
      python_requires='>=3',
      packages=find_packages()
      )
