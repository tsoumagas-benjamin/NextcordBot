import logging

def log():
  #Create logger
  logger = logging.getLogger('nextcord')
  logger.setLevel(logging.DEBUG)

  #Create file handler to write to the log
  handler = logging.FileHandler(filename='nextcord.log', encoding='utf-8', mode='w')

  #Format log entries
  handler.setFormatter(logging.Formatter(fmt='%(asctime)s | %(levelname)s: %(message)s \n', datefmt='%m/%d/%Y %I:%M:%S %p'))
  #Add file handler to logger
  logger.addHandler(handler)