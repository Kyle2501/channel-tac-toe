#!/usr/bin/python2.4
#
# Copyright 2010 Google Inc. All Rights Reserved.

# pylint: disable-msg=C6310

"""Channel Tic Tac Toe

This module demonstrates the App Engine Channel API by implementing a
simple tic-tac-toe game.
"""

import datetime
import logging
import os
import random
from django.utils import simplejson
from google.appengine.api import channel
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


class Game(db.Model):
  """All the data we store for a game"""
  userX = db.UserProperty()
  userY = db.UserProperty()
  board = db.StringProperty()
  moveX = db.BooleanProperty()


class GameUpdater():
  game = None

  def __init__(self, game):
    self.game = game

  def send_update(self):
    gameUpdate = {
      'board': self.game.board,
      'userX': self.game.userX.user_id(),
      'userY': '' if not self.game.userY else self.game.userY.user_id(),
      'moveX': self.game.moveX
    }

    message = simplejson.dumps(gameUpdate)
    channel.send_message(self.game.userX.user_id() + self.game.key().id_or_name(), message)
    if self.game.userY:
      channel.send_message(self.game.userY.user_id() + self.game.key().id_or_name(), message)


class GameFromRequest():
  game = None;
  
  def __init__(self, request):
    user = users.get_current_user()
    game_key = request.get('g')
    if user and id:
      self.game = Game.get_by_key_name(game_key)
      
  def get_game(self):
    return self.game


class MovePage(webapp.RequestHandler):

  def post(self):
    game = GameFromRequest(self.request).get_game()
    user = users.get_current_user()
    id = int(self.request.get('i'))
    if id >= 0 and game and user == game.userX or user == game.userY:
      if game.moveX == (user == game.userX):
        boardList = list(game.board)
        if (boardList[id] == ' '):
          boardList[id] = 'X' if game.moveX else 'Y'
          game.board = "".join(boardList)
          game.moveX = not game.moveX
          game.put()
          GameUpdater(game).send_update()
          self.response.out.write('ok')
          return
    self.response.out.write('no')
    
    
class OpenedPage(webapp.RequestHandler):
  def post(self):
    game = GameFromRequest(self.request).get_game()
    GameUpdater(game).send_update()


class MainPage(webapp.RequestHandler):
  """The main UI page, renders the 'index.html' template."""

  def get(self):
    """Renders the main page. When this page is shown, we create a new
    channel to push asynchronous updates to the client."""
    user = users.get_current_user()
    game_key = self.request.get('g')
    game = None
    if user:
      if not game_key:
        game_key = user.user_id()
        token = 'x'
        while len(token) % 4 != 0:
          game_key = game_key + 'x'
          token = channel.create_channel(user.user_id() + game_key)

        game = Game(key_name = game_key,
                    userX = user,
                    moveX = True,
                    board = '         ')
        game.put()
      else:
        token = channel.create_channel(user.user_id() + game_key)
        game = Game.get_by_key_name(game_key)
        if not game.userY:
          game.userY = user
          game.put()
          
      if game:
        template_values = {'token': token,
                           'me': user.user_id(),
                           'moveX': game.moveX,
                           'board': game.board,
                           'game_key': game_key,
                           'userX': game.userX.user_id(),
                           'userY': '' if not game.userY else game.userY.user_id()}
        path = os.path.join(os.path.dirname(__file__), 'index.html')

        self.response.out.write(template.render(path, template_values))
      else:
        self.response.out.write('No such game')
    else:
      self.redirect(users.create_login_url(self.request.uri))


application = webapp.WSGIApplication([
    ('/', MainPage),
    ('/opened', OpenedPage),
    ('/move', MovePage)], debug=True)


def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
