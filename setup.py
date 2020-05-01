from setuptools import setup
setup(name='avalon-irc',
	version='0.1.0',
	packages=['avalon_irc'],
	entry_points={
		'console_scripts': [
			'avalon-irc = avalon_irc.bot:main'
		]
	},
)