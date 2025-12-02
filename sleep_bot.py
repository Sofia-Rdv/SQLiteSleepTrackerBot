import os
import telebot
from telebot import types
from datetime import datetime
from collections import defaultdict
import json

MY_TOKEN_BOT = os.getenv("API_TOKEN")
bot = telebot.TeleBot(MY_TOKEN_BOT)

