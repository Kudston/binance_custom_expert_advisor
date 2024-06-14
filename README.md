Steps to using file

- move into the project root directory.
- you might want to create a virtual environment
- use "pip install -r requirements.txt"
- setup your api keys and password in the config file, which is located inside the src folder
- navigate to src in your command line
- use 'python bot_start.py' to start the bot
- watchout for its activities on the terminal

Notes:
    - the tp values can be set for each symbol by specifying a list (e.g=>[100, 200, 300]) if the list does not cover the number of pairs in the pairs list, the first value is used for other pairs.
    "" Same thing also applies to atrPurchaseValue and maxSpread

    ---very important note
    - currently working with bybit exchange api
    - your specified pairs has to be in hedge mode
    - only for trading futures 