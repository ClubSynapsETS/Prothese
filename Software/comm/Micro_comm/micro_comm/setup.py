from setuptools import setup

setup(name='micro_comm',
      version='0.2',
      description='',
      long_description="Implematation of bluetooth low energy GATT server using DBUS firmware.\
      It is modified to connect to a specific ESP32 microcontroller",
      url='http://github.com/ClubSynapseETS/Prothese',
      author='Zacharie Bolduc',
      author_email='zachariebolduc@gmail.com',
      packages=setuptools.find_packages(),
      classifiers=[
          "Programming Language :: Python :: 3",
          "Operating System :: Linux",
      ],
      zip_safe=False)
