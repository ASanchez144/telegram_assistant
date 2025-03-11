from setuptools import setup, find_packages

setup(
    name='telegram_openai_assistant',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'python-telegram-bot==20.6',  # Make sure to specify the correct versions
        'openai',
        'Flask',
        'python-dotenv',
        # Add other dependencies here
    ],
    entry_points={
        'console_scripts': [
            'chatbot = telegram_openai_assistant.bot:main',
            'keepalive=keep_alive:start_keep_alive' 
        ],
    },
)
