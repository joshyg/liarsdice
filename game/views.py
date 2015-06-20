# Create your views here.
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.core.context_processors import csrf
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from game.models import Game, UserProfile, GameRequest
from django.contrib.auth.models import User
from django.utils import simplejson
import random
from game import LiarsDice
#from jchat import views
from jchat.models import Room
import re
import string
#global parameters
debug = False
NUM_DICE = 5
main_page = {
  'laptop' : 'ajax_main.html',
  'mobile' : 'mobile_main.html'
}
index_page = {
  'laptop' : 'index.html',
  'mobile' : 'mobile_index.html'
}

def main(request):
  csrf_request = {}
  response_cookie_dict = {}
  debug_log = []
  session_id = request.session.get('_auth_user_id', -1)
  if(session_id == -1):
    return login_page(request)
  print "in main()"
  user = User.objects.get(pk=session_id)
  csrf_request['username'] = str(user) 
  userprofile = UserProfile.objects.get(user=user)
  debug_log.append('logged in!!')
  dice_list = []

  ##determine whether we are in a mobile platform
  platform = get_platform(request.get_signed_cookie('platform', 'x86'))

  #if we are playing the cpu then our turn is always 1, otherwise we can find it stored in a cookie and in the db
  playing_cpu = int(request.GET.get('playing_cpu', 0))
  debug_log.append('playing_cpu read from GET as %s' % str(playing_cpu))
  if(playing_cpu == 1):
    turn = 1 
  else:
    turn = userprofile.turn
  debug_log.append('player turn is %d after turn assignment block' %turn)
  print 'player turn is %d after turn assignment block' %turn

  #exit game flow
  if(int(request.GET.get('exit_game', -1)) == 1):
    debug_log.append('Exiting game')
    response = render_to_response(index_page[platform],  csrf_request, context_instance=RequestContext(request))
    response.set_signed_cookie('at_index', 'True')
    response.set_signed_cookie('inagame', 'False')
    if(not (request.get_signed_cookie('playing_cpu', default=-1) == '1' or playing_cpu == 1)):
      cookie_game_id = int(request.get_signed_cookie('game_id'))
      if(len(GameRequest.objects.filter(pk=cookie_game_id)) > 0):
        try: 
          gamerequest = GameRequest.objects.get(pk=cookie_game_id)
        except:
          gamerequest = -1
        if(gamerequest != -1):
          if(gamerequest.host == user):
            gamerequest.delete() 
    return response

  #inagame is used to determine if we should redirect to index page
  get_inagame = int(request.GET.get('inagame', -1))
  if(( (request.get_signed_cookie('playing_cpu', default=-1) != '1' and playing_cpu != 1))):
    if(len(Game.objects.filter(pk=get_request_param(request,'game_id', -1))) > 0):
      in_defunct_game = False
    else:
      in_defunct_game = True
  else:
    in_defunct_game = False
    
  if((request.get_signed_cookie('inagame', 'False') == 'False' and get_inagame != 1) or in_defunct_game):
    username = User.objects.get(pk=session_id)
    csrf_request = { 'username' : str(username) }
    response = render_to_response(index_page[platform],  csrf_request, context_instance=RequestContext(request))
    response.set_signed_cookie('at_index', 'True')
    return response

  #the previous_game_fsm value will not be affected by posted form data
  #therefore it should only equal game_fsm when there is a refresh
  #if we're plying_cpu we set previous_game_fsm to NA, so it will never = game_fsm
  if(playing_cpu != 1):
    previous_game_fsm = request.get_signed_cookie('game_fsm', 0)
  else:
    previous_game_fsm = 'NA'
  game_fsm = get_request_param(request,'game_fsm', 0)
  if(playing_cpu != 1 and game_fsm == 0):
    game_fsm = request.get_signed_cookie('game_fsm', 0)
    debug_log.append('game_fsm cookie read,')
  debug_log.append(' game_fsm = %s previous_game_fsm = %s' % (str(game_fsm), str(previous_game_fsm)))
  print ' game_fsm = %s previous_game_fsm = %s' % (str(game_fsm), str(previous_game_fsm))
  if(get_request_param(request,'submit_type', 0) == 'New Game'):
    #for now, the new game button should only appear when we are playing the cpu.  
    #otherwise a new request should be launched
    playing_cpu = 1
    game_fsm = 0
    if(len(Game.objects.filter(pk=get_request_param(request,'game_id', -1))) > 0):
      game = get_object_or_404(Game, pk=get_request_param(request,'game_id', -1)) 
      game.delete()
  csrf_request['game_fsm'] = game_fsm

  #############################
  ##beginning of game FSM logic
  #############################

  print 'game_fsm = %s' %(str(game_fsm))
  debug_str = get_request_param(request, 'debug_str', 'NA')
  print '%s debug_str = %s' %(user, debug_str)

  ##rolls should occur regardless of whether it is our turn
  if(game_fsm == "has_rolled" or game_fsm == "reroll"):
    debug_str = get_request_param(request, 'debug_str', 'NA')
    print '%s has_rolled/reroll, submit_type != bullshit, debug_str = %s' %(user, debug_str)
    if(request.get_signed_cookie('playing_cpu', default=-1) == '1' or playing_cpu == 1):
      debug_log.append('in playing_cpu and (has_rolled or reroll) block')
      print 'in playing_cpu and (has_rolled or reroll) block'

      #generate player roll
      userprofile.roll = 0 
      if(game_fsm == "has_rolled"):
        userprofile.num_dice = NUM_DICE 
      for i in range(userprofile.num_dice):
        roll = random.randint(1,6)
        dice_list.append(roll)
        userprofile.roll += roll*(10**(i))
        print "roll = %d" % userprofile.roll
      userprofile.save()
      if(game_fsm == "has_rolled"):
        game = Game(num_players=2, has_cpu=True, log = '', num_cpu_dice = NUM_DICE, turn=1, timestamp=0)
        game.num_dice = game.num_players*NUM_DICE
      else:
        game = get_object_or_404(Game, pk=get_request_param(request,'game_id', -1)) 

      #generate cpu roll->only on cpu game
      game.cpu_roll = 0 
      for i in range(game.num_cpu_dice):
        roll = random.randint(1,6)
        game.cpu_roll += roll*(10**(i))
        print "roll = %d" % game.cpu_roll
      game.save()
      print "game_id = %d" %game.id
      csrf_request['game_id'] = game.id
      csrf_request['game_fsm'] = 'has_rolled'
      csrf_request['log'] = re.split('\n', game.log)

      #check if game is over
      if(game_fsm == "reroll" and (game.num_cpu_dice == 0 or userprofile.num_dice == 0)):
        csrf_request['game_fsm'] = 'game_over'
        if(game.num_cpu_dice == 0):
          csrf_request['winner'] = '%s' %(string.upper(str(csrf_request['username'])))
        else:
          csrf_request['winner'] = 'CPU'

    ## multiplayer, (game_fsm == "has_rolled" or game_fsm == "reroll")
    else:
      #generate player roll, but not on refresh
      if(game_fsm != previous_game_fsm):
        debug_log.append('rerolling...')
        userprofile.roll = 0 
        for i in range(userprofile.num_dice):
          roll = random.randint(1,6)
          dice_list.append(roll)
          userprofile.roll += roll*(10**(i))
          print "roll = %d" % userprofile.roll
        userprofile.save()
      else:
        debug_log.append('not rerolling...')
        dice_list = get_roll_from_int(userprofile.roll, userprofile.num_dice)

      ##must have all players join the same game
      ##assume this game was created by hosts request
      cookie_game_id = int(request.get_signed_cookie('game_id'))
      debug_log.append('game_id cookie read, game_id = %d' % cookie_game_id)
      game = get_object_or_404(Game, pk=cookie_game_id) 
      csrf_request['game_id'] = game.id
      csrf_request['game_fsm'] = 'has_rolled'
      csrf_request['log'] = re.split('\n', game.log)

      #determine if bullshit should be an option by parsing the last line of the logfile
      #if the last line was a claim, its bullshittable.  I like saying bullshittable :)
      if(len(csrf_request['log']) == 1):
        last_line = csrf_request['log'][0]
      else:
        for i in range(1,len(csrf_request['log']) +1):
          last_line = csrf_request['log'][len(csrf_request['log']) - i]
          if(last_line != ''):
            break
        debug_log.append('last_line = %s' %last_line)
      if(re.search(r'claim', last_line)):
        csrf_request['bullshittable'] = 1
      else:
        csrf_request['bullshittable'] = 0

      #If there are more than 2 players then we can make a has_rolled to reroll transition when another player calls bullshit
      #for instance if i am player 1, I roll, player 2 makes a claim, and player 3 calls bullshit
      #of course, if the amount of players goes from 3->2, this condition fails:
      #if(game.num_players > 2 and game.log != ''):
      #so i am loosening it
      if(game.log != ''):
        get_bullshit_tuple = get_bullshit_call(game.log)
        if(get_bullshit_tuple[0] == False):
          csrf_request['value'] = request.get_signed_cookie('value', 0)
          csrf_request['amount'] = request.get_signed_cookie('amount', 0)
          debug_log.append('bullshit was not called')
          print ' username = %s bullshit was not called' % str(user)
        else:
          #here we ensure that we only circle back to reroll once
          timestamp = game.timestamp
          bullshit_timestamp = int(request.get_signed_cookie('bullshit_timestamp', 0))
          debug_log.append('bullshit was called, timestamp = %d bullshit_timestamp = %d' %(timestamp,bullshit_timestamp))
          print ' username = %s  bullshit was called, timestamp = %d bullshit_timestamp = %d' %(str(user), timestamp,bullshit_timestamp)
          if(game_fsm == 'has_rolled' and (bullshit_timestamp != timestamp or bullshit_timestamp == 0)):
            csrf_request['game_fsm'] = 'reroll'
            response_cookie_dict['bullshit_timestamp'] = timestamp  
            if(game.num_players == 1):
              csrf_request['game_fsm'] = 'game_over'
              csrf_request['winner'] = '%s' %(get_winner(game))
            
        debug_log.append('line = %s' %get_bullshit_tuple[1])

      #check if game is over
      if(userprofile.num_dice == 0):
        if(game.num_players == 1):
          csrf_request['game_fsm'] = 'game_over'
          csrf_request['winner'] = '%s' %(get_winner(game))
        else:
          csrf_request['game_fsm'] = 'eliminated'

  elif((game_fsm == 'has_claimed' or game_fsm == 'reclaim') and get_request_param(request,'submit_type', 0) != 'bullshit!!'):
    debug_str = get_request_param(request, 'debug_str', 'NA')
    print '%s reclaim/has_claimed, submit_type != bullshit, debug_str = %s' %(user, debug_str)
    dice_list = get_roll_from_int(userprofile.roll, userprofile.num_dice)
    ##the following block of code is only executed on cpu games
    if(request.get_signed_cookie('playing_cpu', default=-1) == '1'):
      csrf_request['value'] = get_request_param(request,'value', 0)
      csrf_request['amount'] = get_request_param(request,'amount', 0)
      print 'GET game_id val = %s debug_str = %s' % (request.GET.get('game_id', 'NA'), get_request_param(request, 'debug_str', 'NA'))
      game = get_object_or_404(Game, pk=get_request_param(request,'game_id', -1)) 
      csrf_request['game_id'] = game.id 
      cpu_roll = get_roll_from_int(game.cpu_roll, game.num_cpu_dice)
      if(game.num_dice < game.num_cpu_dice):
        return HttpResponse("Illegal values, num_dice = %d < cpu_dice = %d.  cpu_roll = %s" % (game.num_dice, game.num_cpu_dice, str(cpu_roll)))
      liars_dice_request = {
        'num_dice' : game.num_dice, 
        'cpu_dice' : game.num_cpu_dice, 
        'roll' : cpu_roll, #this is the cpus roll, not mine 
        'claim_value': int(get_request_param(request,'value', 0)),
        'claim_amount' : int(get_request_param(request,'amount', 0)),
        'first_turn' : 'no'#cpu is never first turn for now
      }
      game.log += 'Player claim amount: %d, player claim value: %d\n' %(liars_dice_request['claim_amount'], liars_dice_request['claim_value'])
      print liars_dice_request
      cpu_response = LiarsDice.LiarsDice(webmode=True, request=liars_dice_request)
      if(cpu_response.BullShit):
        print "Cpu says bullshit!!"
        csrf_request['cpu_response'] = "Cpu says bullshit!!"
        csrf_request['game_fsm'] = 'reroll'
        game.log += csrf_request['cpu_response']
        int_claim_value = int(csrf_request['value'])
        int_claim_amount = int(csrf_request['amount'])
        int_actual_amount = dice_list.count(int_claim_value) + dice_list.count(1) + cpu_roll.count(int_claim_value) + cpu_roll.count(1) 
        if(int_actual_amount >= int_claim_amount):
           game.log += ' CPU is wrong!! actual amount of '+str(int_claim_value)+'\'s is '+str(int_actual_amount)+'\n'
           game.num_cpu_dice -= 1
           game.num_dice -= 1
           if(game.num_cpu_dice == 0):
             csrf_request['game_fsm'] = 'game_over'
             csrf_request['winner'] = '%s' %(string.upper(str(csrf_request['username'])))
        else:
           game.log += ' CPU is right!! actual amount of '+str(int_claim_value)+'\'s is '+str(int_actual_amount)+'\n'
           game.num_dice -= 1
           userprofile.num_dice -= 1
           if(userprofile.num_dice == 0):
             csrf_request['game_fsm'] = 'game_over'
             csrf_request['winner'] = 'CPU'

      else:
        print "Cpu claims %d %d's" % (cpu_response.cpu_claim_amount, cpu_response.cpu_claim_value)
        csrf_request['cpu_response'] = "Cpu claims %d %d's\n" % (cpu_response.cpu_claim_amount, cpu_response.cpu_claim_value)
        csrf_request['cpu_claim_amount'] = int(cpu_response.cpu_claim_amount)
        csrf_request['cpu_claim_value'] = int(cpu_response.cpu_claim_value)
        game.log += csrf_request['cpu_response']

    #multiplayer game, ((game_fsm == 'has_claimed' or game_fsm == 'reclaim') and get_request_param(request,'submit_type', 0) != 'bullshit!!')
    else:
      debug_str = get_request_param(request, 'debug_str', 'NA')
      print 'user = %s multiplayer, has_claimed or reclaim, submit_type != bullshit, debug_str = %s' %(str(user), debug_str) 
      game = get_object_or_404(Game, pk=request.get_signed_cookie('game_id'))
      csrf_request['game_id'] = game.id 
      if(game_fsm != previous_game_fsm):
        print 'game_fsm = %s previous_game_fsm = %s, debug_str = %s' %(str(game_fsm), str(previous_game_fsm), debug_str) 
        csrf_request['value'] = get_request_param(request,'value', 0)
        csrf_request['amount'] = get_request_param(request,'amount', 0)
        game = get_object_or_404(Game, pk=get_request_param(request,'game_id', -1)) 
        csrf_request['game_id'] = game.id 
        game.log += '%s claims %d %d\'s\n' %(csrf_request['username'], int(csrf_request['amount']), int(csrf_request['value']))
        game.timestamp += 1
      else:
        print 'game_fsm = previous_game_fsm, so this is a bullshit_refresh'

        #this block determines whether bullshit was called
        get_bullshit_tuple = get_bullshit_call(game.log)
        if(get_bullshit_tuple[0] == False):
          csrf_request['value'] = request.get_signed_cookie('value', 0)
          csrf_request['amount'] = request.get_signed_cookie('amount', 0)
          debug_log.append('bullshit was not called')
          print 'bullshit was not called'
        else:
          csrf_request['game_fsm'] = 'reroll'
          debug_log.append('bullshit was called')
          print 'bullshit was called'
          timestamp = game.timestamp
          response_cookie_dict['bullshit_timestamp'] = timestamp  

          #check if game is over
          if(userprofile.num_dice == 0):
            if(game.num_players == 1):
              csrf_request['game_fsm'] = 'game_over'
              csrf_request['winner'] = '%s' %(get_winner(game))
            else:
              csrf_request['game_fsm'] = 'eliminated'
          elif(game.num_players == 1):
            csrf_request['game_fsm'] = 'game_over'
            ##this could be more efficient.  if user has > 0 dice and 1 player remains, he/she is the winner
            csrf_request['winner'] = '%s' %(get_winner(game))
        debug_log.append('line = %s' %get_bullshit_tuple[1])
    csrf_request['log'] = re.split('\n', game.log)
    game.save()

  elif((game_fsm == 'reclaim' or game_fsm == 'has_claimed')  and get_request_param(request,'submit_type', 0) == 'bullshit!!'):
    debug_str = get_request_param(request, 'debug_str', 'NA')
    print '%s reclaim/has_claimed, submit_type = bullshit, debug_str = %s' %(user, debug_str)

    ##following evaluates bullshit claim when playing cpu
    dice_list = get_roll_from_int(userprofile.roll, userprofile.num_dice)
    if(request.get_signed_cookie('playing_cpu', default=-1) == '1'):
      int_claim_value = int(get_request_param(request,'cpu_claim_value', 0))
      int_claim_amount = int(get_request_param(request,'cpu_claim_amount', 0))
      game = get_object_or_404(Game, pk=get_request_param(request,'game_id', -1)) 
      csrf_request['game_id'] = game.id 
      game.log += '%s calls bullshit!! ' %(user)
      cpu_roll = get_roll_from_int(game.cpu_roll, game.num_cpu_dice)
      if(dice_list.count(int_claim_value) + dice_list.count(1) + cpu_roll.count(int_claim_value) + cpu_roll.count(1) >= int_claim_amount):
        print 'subtracting num_dice'
        game.log += 'he/she is Wrong!!\n' 
        game.num_dice -= 1
        userprofile.num_dice -= 1
        if(userprofile.num_dice == 0):
          csrf_request['game_fsm'] = 'game_over'
          csrf_request['winner'] = 'CPU'
      else:
        print 'subtracting num_dice'
        game.log += 'he/she is Correct!!\n' 
        game.num_dice -= 1
        game.num_cpu_dice -= 1
        if(game.num_cpu_dice == 0):
          csrf_request['game_fsm'] = 'game_over'
          csrf_request['winner'] = '%s' %(string.upper(str(user)))

    #multiplayer, ((game_fsm == 'reclaim' or game_fsm == 'has_claimed')  and get_request_param(request,'submit_type', 0) == 'bullshit!!')
    else:
      game = get_object_or_404(Game, pk=request.get_signed_cookie('game_id'))
      log_array = re.split(r'\n', game.log)
      log_array.reverse()
      for line in log_array:
        line_re = re.search(r'claims\s+(\d+)\s+(\d+)\'s', line)
        if(line_re != None):
          int_claim_amount = int(line_re.groups(0)[0]) 
          int_claim_value = int(line_re.groups(0)[1])
          break
      debug_log.append('bullshit called on claim_amount %d claim_value %d' %(int_claim_amount, int_claim_value))
      csrf_request['game_id'] = game.id 
      game.log += '%s calls bullshit!!' %(user)
      game.timestamp += 1

      ##evaluate bullshit when  playing other players
      count = 0
      for player in game.players.all():
        player_profile = UserProfile.objects.get(user=player)
        player_roll =  get_roll_from_int(player_profile.roll, player_profile.num_dice)
        count += (player_roll.count(int_claim_value) + player_roll.count(1))
      if(count>= int_claim_amount):
        game.log += ' he/she is Wrong!!' 
        print 'subtracting num_dice'
        game.num_dice -= 1
        userprofile.num_dice -= 1
        userprofile.save()
        losers_turn = userprofile.turn

        #winner must go first next round
        game.turn = (userprofile.turn - 1)%game.num_players
        if(game.turn == 0):
          game.turn = game.num_players

        #if previous player out of game, we must shift turns of all players
        if(userprofile.num_dice == 0):
          game.log += ' %s eliminated!!\n' % (csrf_request['username'])
          csrf_request['game_fsm'] = 'eliminated'
          shift_players = True
        else:
          game.log += '\n'
          shift_players = False 
      else:
        ##following evaluates bullshit claim when playing multiplayer
        game.log += ' he/she is Correct!!' 
        game.num_dice -= 1
        print 'subtracting num_dice'

        #winner must go first next round
        game.turn = userprofile.turn
        for player in game.players.all():
          player_profile = UserProfile.objects.get(user=player)

          ##special case:  user is turn 1.  requires special handling because previous player actually has turn = game.num_players
          ##solution:  create tmp 'turn' variable.  set to 0 if player_profile.turn = game.num_players
          tmp_player_profile_turn = player_profile.turn
          if(tmp_player_profile_turn == game.num_players):
            tmp_player_profile_turn = 0
          if(tmp_player_profile_turn == (userprofile.turn-1)%game.num_players and player_profile.num_dice > 0):
            previous_player = UserProfile.objects.get(user=player)
            previous_player.num_dice -= 1
            previous_player.save()
            losers_turn = previous_player.turn

            #if previous player out of game, we must shift turns of all players
            if(previous_player.num_dice == 0):
              game.log += '%s eliminated!!\n' % (player)
              debug_log.append( '%s eliminated!!\n' % (player))
              shift_players = True
            else:
              game.log += '\n'
              shift_players = False 
            break

      #if previous player out of game, we must shift turns of all players
      debug_log.append('shift_players = %s' % str(shift_players))
      debug_log.append('before shift %s has turn %d' %(user, userprofile.turn))
      if(shift_players):
        game.num_players -= 1
        debug_log.append('game.num_players = %d' % (game.num_players))
        for player in game.players.all():  
          player_profile = UserProfile.objects.get(user=player)
          if(player_profile.turn >= losers_turn and player_profile != userprofile):
            debug_log.append('shifting turn of player %s' % (player))
            up = UserProfile.objects.get(user=player)
            up.turn-=1
            up.save()
        if(userprofile.turn >= losers_turn):

          #current user must be handled differently.  efficiency: can the save be removed?
          userprofile.turn -= 1
          userprofile.save()
        debug_log.append('after shift %s has turn %d' %(user, userprofile.turn))

        #if 1 player left, must declare winner
        if(game.num_players == 1):
          csrf_request['game_fsm'] = 'game_over'
          if(userprofile.num_dice != 0):
            csrf_request['winner'] = '%s' % (string.upper(str(csrf_request['username'])))
          else:
            csrf_request['winner'] = get_winner(game)
    ####end of 'end of game' code

    timestamp = game.timestamp
    response_cookie_dict['bullshit_timestamp'] = timestamp  
    if(csrf_request['game_fsm'] != 'game_over' and csrf_request['game_fsm'] != 'eliminated'):
      csrf_request['game_fsm'] = 'reroll'
    csrf_request['log'] = re.split('\n', game.log)
    game.save()
  if(game_fsm == 'eliminated'):
    debug_log.append('You have been eliminated')
    game = get_object_or_404(Game, pk=request.get_signed_cookie('game_id'))
    if(game.num_players == 1):
      csrf_request['game_fsm'] = 'game_over'
      csrf_request['winner'] = get_winner(game)
     

  csrf_request['dice_list'] = dice_list
  userprofile.save()

  ##I don't want to set turn when game_fsm=0, at this point we are rolling, and its really noones turn yet
  ##I also don't want to save game, since it hasn't begun
  if(request.get_signed_cookie('playing_cpu', default=-1) == '1' or playing_cpu == 1):
    csrf_request['playing_cpu'] = 1
    csrf_request['my_turn'] = 1
    if(game_fsm == 0 and get_request_param(request,'multiplayer_begin', False)):
      csrf_request['game_id'] = game.id
  else:
    csrf_request['playing_cpu'] = 0
    if(game_fsm != 0 and game_fsm != 'game_over'):

      #the following occurs when last player calls bullshit, is shifted down
      if(game.turn > game.num_players):
        game.turn = game.num_players
      if(game.turn == userprofile.turn and userprofile.num_dice > 0):
        csrf_request['my_turn'] = 1

        #turns only increment on claims
        if(game_fsm != previous_game_fsm and game_fsm != 'has_rolled' and game_fsm != 'reroll' and get_request_param(request,'submit_type', 0) != 'bullshit!!'):

          #if you've claimed, its no longer your turn.  Increment game counter
          csrf_request['my_turn'] = 0

          #modulo addtion, but count from 1 to num_playes
          game.turn = (game.turn + 1) % game.num_players
          if(game.turn == 0):
            game.turn = game.num_players
      else:
        csrf_request['my_turn'] = 0

      #if game length > 2300 we must remove some lines, adjust bullshit timestamp accordingly
      if(len(game.log) > 2300):
        game.log = game.log[500:len(game.log)]
      game.save()
    elif( get_request_param(request,'multiplayer_begin', False)):
      csrf_request['game_id'] = game.id
  ####
  if(request.get_signed_cookie('playing_cpu', default=-1) != '1' and playing_cpu != 1):
    debug_log.append('player turn = %d game turn = %d my_turn = %d' %(userprofile.turn, game.turn, csrf_request['my_turn']))
    print 'player  = %s turn = %d game turn = %d my_turn = %d' %(csrf_request['username'], userprofile.turn, game.turn, csrf_request['my_turn'])
    debug_log.append('in response, csrf_request game_fsm = %s' %csrf_request['game_fsm'])
  csrf_request['debug_log'] = debug_log

  #only print last line(for now, may change later)
  if(len(csrf_request.get('log', [])) >= 2):
    csrf_request['log'] = csrf_request['log'][-2:-1]
  if(debug == False):
    csrf_request['debug_log'] = []

  #helps determine if page load is the result of an ajax autosubmission
  csrf_request['autosubmission'] = get_request_param(request,'autosubmission', 0)
  
  if(request.get_signed_cookie('playing_cpu', default=-1) != '1' and playing_cpu != 1):
    csrf_request['timestamp'] = game.timestamp 
  
  csrf_request.update(csrf(request))
  if(get_request_param(request,'ajax_submission', 0) == 0):
    response = render_to_response(main_page[platform],  csrf_request, context_instance=RequestContext(request))
    print 'main returning a normal rendeer_to_response'
  else:
    print 'main returning a json response'
    json_request_dict = {}
    json_request_dict['my_turn'] = csrf_request.get('my_turn', 0)
    json_request_dict['game_fsm'] = csrf_request.get('game_fsm', 0)
    json_request_dict['dice_list'] = csrf_request.get('dice_list', 0)
    json_request_dict['log'] = csrf_request.get('log', '')
    json_request_dict['game_id'] = csrf_request.get('game_id', -1)
    json_request_dict['bullshittable'] = csrf_request.get('bullshittable', 0)
    json_request_dict['winner'] = csrf_request.get('winner', 'NA')
    json_request_dict['username'] = csrf_request.get('username', '')
    if(request.get_signed_cookie('playing_cpu', default=-1) == '1' or playing_cpu == 1):
      json_request_dict['last_claim_amount'] = csrf_request.get('cpu_claim_amount', 0)
      json_request_dict['last_claim_value'] = csrf_request.get('cpu_claim_value', 0)
    print 'populated json dict'
   
    json_str = simplejson.dumps(json_request_dict) 
    print "main() json_str:"
    print json_str 
    response = HttpResponse(json_str, mimetype='application/json') 
    print 'response assigned'
    
  #save state in a cookie, necessarry for autorefresh
  response.set_signed_cookie('game_fsm', csrf_request['game_fsm'])
  response.set_signed_cookie('previous_game_fsm', previous_game_fsm)
  if(csrf_request.get('claim_value', -1) != -1):
    response.set_signed_cookie('claim_value', csrf_request['claim_value'])
  if(csrf_request.get('claim_amount', -1) != -1):
    response.set_signed_cookie('claim_amount', csrf_request['claim_amount'])
  if(get_inagame == 1):
    response.set_signed_cookie('inagame', 1)
  if(playing_cpu == 1):
    response.set_signed_cookie('playing_cpu', 1)
  for key,val in response_cookie_dict.iteritems():
    response.set_signed_cookie(key,val)
  print 'returning response!!'
  return response

def create_user(request):
  username = get_request_param(request,'new_username', '')
  password = get_request_param(request,'new_password', '')
  platform = get_request_param(request,'platform', 'x86')
  if(password != '' and username != ''):
    if(len(User.objects.filter(username=username)) == 0):
      new_user = User(username=username)
      new_user.set_password(password)
      new_user.save()
      user = authenticate(username=username, password=password)
      login(request, user)
      response = HttpResponseRedirect(reverse('game.views.main'))
      response.set_signed_cookie('inagame', 'False')
      #set default platform to x86
      response.set_signed_cookie('platform', get_request_param(request, 'platform', 'x86'))
      print "at end of create_user"
      return response
    
    else:
      return HttpResponse('Username taken!  Be More original!')
  else:
    return HttpResponse('no entry given!!')
     
def login_page(request):
  csrf_request = {}
  csrf_request.update(csrf(request))
  return render_to_response('login.html', csrf_request)

def logout_user(request):
  logout(request)
  return HttpResponseRedirect(reverse('game.views.login_page'))

def authenticate_user(request):
    csrf_request = {}
    csrf_request.update(csrf(request))
    username = request.POST['username']
    password = request.POST['password']
    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            login(request, user)
            # Redirect to a success page.
            response = HttpResponseRedirect(reverse('game.views.main'))
            response.set_signed_cookie('inagame', 'False')
            #set default platform to x86
            response.set_signed_cookie('platform', get_request_param(request, 'platform', 'x86'))
            return response

        else:
            # Return a 'disabled account' error message
            return HttpResponse("Account disabled, hit back on your browser to try again")
    else:
        # Return an 'invalid login' error message.
        return HttpResponse("Invalid Login, hit back on your browser to try again")

def request_game(request):
  session_id = request.session.get('_auth_user_id', -1)
  if(session_id == -1):
    return login_page(request)
  username = User.objects.get(pk=session_id)
  platform = get_platform(request.get_signed_cookie('platform', 'x86'))
  if(request.get_signed_cookie('at_index', default='False') == 'True'):
    if(len(GameRequest.objects.filter(host=username)) >= 1):
      #return HttpResponse("Can Only host one game at a time!!")
      csrf_request = {'username' : str(username)}
      return render_to_response('delete_req.html',csrf_request, context_instance=RequestContext(request))
    num_players = get_request_param(request,'num_players', 0)
    has_cpu = get_request_param(request,'has_cpu', 0)
    gamerequest = GameRequest(requested_players=num_players, accepted_players=1, has_cpu=has_cpu, host=username)
    gamerequest.save()
    gamerequest.player_names.add(username)
    gamerequest.save()
    game = Game(num_players=num_players, has_cpu=False, log = '', num_cpu_dice = 0, turn=1, pk=gamerequest.id, cpu_roll=0, num_dice = NUM_DICE*num_players, timestamp=0)
    game.save()
    #chat related?
    room = Room(id=game.id)
    room.save()
    userprofile = UserProfile.objects.get(user=username)
    userprofile.turn=1
    userprofile.num_dice = NUM_DICE 
    userprofile.save()
    csrf_request = {'message' : 'waiting'} 
    csrf_request.update(csrf(request))
    response = render_to_response('wait.html',  csrf_request, context_instance=RequestContext(request))
    response.set_signed_cookie('at_index', 'False')
    response.set_signed_cookie('gamerequest_id', str(gamerequest.id))
    #originally i stored turn in a cookie.  then i realized it was not feasible because
    #one player must know the turns of the others, so i now store in db.  I may remove the
    #cookie later
    response.set_signed_cookie('turn', 1)
    response.set_signed_cookie('playing_cpu', 0)
    return response
  else:
    int_gamerequest_id = int(request.get_signed_cookie('gamerequest_id'))
    try:
      gamerequest = GameRequest.objects.get(pk=int_gamerequest_id)
    except:
      gamerequest = -1
    if(gamerequest == -1):
      csrf_request = {} 
      csrf_request.update(csrf(request))
      return render_to_response(index_page[platform],  csrf_request, context_instance=RequestContext(request))
       
    #during development, >= will save me time.  later should make ==
    #if(gamerequest.accepted_players >= gamerequest.requested_players):
    if(gamerequest.accepted_players == gamerequest.requested_players):
      try:
        game = Game.objects.get(pk=gamerequest.id)
      except:
        game = -1
      if(game == -1):
        csrf_request = {} 
        csrf_request.update(csrf(request))
        return render_to_response(index_page[platform],  csrf_request, context_instance=RequestContext(request))
      game.players = gamerequest.player_names.all()
      game.save()
      csrf_request = {'multiplayer_begin':True, 
                      'host' : gamerequest.host, 
                      'num_players' : gamerequest.requested_players,
                      'game_fsm' : 0,
                      'playing_cpu' : 0,
                      'username' : str(username),
                      'dice_list' : [],
                      'game_id' : gamerequest.id#this doesn't seem to be working due to auto refresh 
                     }
      csrf_request.update(csrf(request))
      response = render_to_response(main_page[platform],  csrf_request, context_instance=RequestContext(request))
      response.set_signed_cookie('inagame', 'True')
      response.set_signed_cookie('game_id', gamerequest.id)
      response.set_signed_cookie('game_fsm', 0)
      response.set_signed_cookie('bullshit_timestamp', 0)
      return response
    elif(gamerequest.accepted_players < gamerequest.requested_players):
      csrf_request = {'message' : 'still waiting'} 
      csrf_request.update(csrf(request))
      response = render_to_response('wait.html',  csrf_request, context_instance=RequestContext(request))
      return response
    else:
      #if accepted_players > requested players then the user has probably hit back on browser
      #and attempted to reentered.  don't allow, redirect to index
      csrf_request = {} 
      csrf_request.update(csrf(request))
      return render_to_response(index_page[platform],  csrf_request, context_instance=RequestContext(request))

    
    

def join_game(request):
  session_id = request.session.get('_auth_user_id', -1)
  if(session_id == -1):
    return login_page(request)
  requested_game = request.GET.get('requested_game', 'None')
  username = User.objects.get(pk=session_id)
  platform = get_platform(request.get_signed_cookie('platform', 'x86'))
  print 'in join_game'
  if(requested_game == 'None'): 
    #req_list = GameRequest.objects.all() 
    req_list = GameRequest.objects.exclude(host = username) 
    unfilled_req_list = []
    for gr in req_list:
      if (gr.requested_players > gr.accepted_players):
        unfilled_req_list.append(gr)
    csrf_request = {'req_list' : unfilled_req_list }
    csrf_request.update(csrf(request))
    response = render_to_response('join.html',  csrf_request, context_instance=RequestContext(request))
    response.set_signed_cookie('first_visit', 'True')
    return response
  else:
    try:
      gamerequest = GameRequest.objects.get(pk=int(requested_game))
    except:
      gamerequest = -1
    if(gamerequest == -1):
      csrf_request = {}
      csrf_request.update(csrf(request))
      return render_to_response(index_page[platform],  csrf_request, context_instance=RequestContext(request))
    if(request.get_signed_cookie('first_visit', default='False') == 'True'):
      print 'first visit'
      gamerequest.accepted_players+=1
      gamerequest.player_names.add(username)
      gamerequest.save()
    #during development, >= will save me time.  later should make ==
    if(gamerequest.accepted_players == gamerequest.requested_players):
        csrf_request = {'multiplayer_begin':True, 
                        'host' : gamerequest.host, 
                        'num_players' : gamerequest.requested_players,
                        'game_fsm' : 0,
                        'dice_list' : [],
                        'username' : str(username),
                        'game_id' : gamerequest.id,#this may not work due to autorefresh
                        'playing_cpu' : 0,
                       }
        csrf_request.update(csrf(request))
        response = render_to_response(main_page[platform],  csrf_request, context_instance=RequestContext(request))
        response.set_signed_cookie('inagame', 'True')
        response.set_signed_cookie('game_id', gamerequest.id)
        response.set_signed_cookie('game_fsm', 0)
        #if a turn hasn't been assigned (implying this is the first visit), assign the last turn
        #originally i stored turn in a cookie.  then i realized it was not feasible because
        #one player must know the turns of the others, so i now store in db.  I may remove the
        #cookie later
        #if(request.get_signed_cookie('turn', default='False') == 'False'):
        if(request.get_signed_cookie('first_visit', default='False') == 'True'):
          response.set_signed_cookie('turn', str(gamerequest.requested_players))
          response.set_signed_cookie('playing_cpu', 0)
          response.set_signed_cookie('bullshit_timestamp', 0)
          response.set_signed_cookie('first_visit', 'False')
          userprofile = UserProfile.objects.get(user=username)
          userprofile.turn = gamerequest.accepted_players
          print 'last player.  assigning %s turn %d' %(username, userprofile.turn)
          userprofile.num_dice = NUM_DICE 
          userprofile.save()
        return response
    elif(gamerequest.accepted_players < gamerequest.requested_players):
      #if(first visit), assign the last turn
      if(request.get_signed_cookie('first_visit', default='False') == 'True'):
        csrf_request = {'message' : 'waiting'} 
        csrf_request.update(csrf(request))
        response = render_to_response('wait.html',  csrf_request, context_instance=RequestContext(request))
        response.set_signed_cookie('first_visit', 'False')
        response.set_signed_cookie('turn', gamerequest.accepted_players)
        username = User.objects.get(pk=session_id)
        userprofile = UserProfile.objects.get(user=username)
        userprofile.turn = gamerequest.accepted_players
        print 'not last player.  assigning %s turn %d' %(username, userprofile.turn)
        userprofile.num_dice = NUM_DICE 
        #the following may only be necessary when game is begun(which is not now!!)
        response.set_signed_cookie('playing_cpu', 0)
        userprofile.save()
      else:
        csrf_request = {'message' : 'still waiting'}
        csrf_request.update(csrf(request))
        response = render_to_response('wait.html',  csrf_request, context_instance=RequestContext(request))
        response.set_signed_cookie('first_visit', 'False')
      return response
    else:
      #if accepted_players > requested players then the user has probably hit back on browser
      #and attempted to reentered.  don't allow, redirect to index
      csrf_request = {} 
      csrf_request.update(csrf(request))
      return render_to_response(index_page[platform],  csrf_request, context_instance=RequestContext(request))

def delete_request(request):
  session_id = request.session.get('_auth_user_id', -1)
  if(session_id == -1):
    return login_page(request)
  username = User.objects.get(pk=session_id)
  platform = get_platform(request.get_signed_cookie('platform', 'x86'))
  if(len(GameRequest.objects.filter(host=username)) >= 1):
    try:
      game_req = GameRequest.objects.get(host=username)
    except:
      game_req = -1
    if(game_req == -1):
      return render_to_response(index_page[platform],  csrf_request, context_instance=RequestContext(request))
    game_req.delete()
  csrf_request = {'username' : str( username )}
  csrf_request.update(csrf(request))
  return render_to_response(index_page[platform],  csrf_request, context_instance=RequestContext(request))
   
   
"""
This method is called by AJAX.  It checks whether it is players turn
"""
def turncheck(request):
  session_id = request.session.get('_auth_user_id', -1)
  if(session_id == -1):
    return login_page(request)
  response = {}
  ##user = User.objects.get(pk=session_id)
  username = User.objects.get(pk=session_id)
  print 'we made it to top of turncheck!!'
  up_set = UserProfile.objects.all()
  for i in up_set:
    if (i.user == username):
      my_userprofile = i
  #my_userprofile = UserProfile.objects.get(user=username)
  game_id = request.GET.get('game_id', 'NA')
  #print 'game_id = %s' % (str(game_id))
  try:
    game = Game.objects.get(pk=game_id)
  except:
    game = -1
  if(game == -1):
    return render_to_response(index_page[platform],  csrf_request, context_instance=RequestContext(request))
  print '%s turn = %d game_turn = %d' %(username,  my_userprofile.turn, game.turn)
  if(game.turn == my_userprofile.turn):
    response['my_turn'] = 1
  else:
    response['my_turn'] = 0
  #in addition t a change in turn, a call of bs can also cause need for a refresh
  bs = get_bullshit_call(game.log)
  print 'get_bullshit_call complete'
  if(bs[0] == True):
    print 'bs = true'
    response['bullshit_called'] = 1
    response['bullshit_timestamp'] = game.timestamp
    #gather dice lists to display oter players rolls after a bullshit
    response['game_players'] = []
    response['player_dice_lists'] = []
    for player in game.players.all():
      response['game_players'] += [str(player)]
      response['player_dice_lists'].append( get_player_dice_list(player) )
  else:
    print 'bs = false'
    response['bullshit_called'] = 0
    response['bullshit_timestamp'] = 0
  print 'bullshit_called assigned log = %s' % game.log 
  log = re.split('\n', game.log)
  response['log'] = log[-2:-1]
  #determine if bullshit should be an option by parsing the last line of the logfile
  #if the last line was a claim, its bullshittable
  last_line = response['log'][-1]
  if(re.search(r'claim', last_line)):
    response['bullshittable'] = 1
    print 'bullshittable'
  else:
    response['bullshittable'] = 0
    print 'not bullshittable'

  (response['last_claim_amount'], response['last_claim_value']) = get_last_claim(game.log) 
  
  #for key, val in response.iteritems():
  #  print '%s => %s' % (key, str(val))
  json_str = simplejson.dumps(response)
  print 'turncheck json_str:'
  print json_str
  return HttpResponse(json_str, mimetype='application/json') 

"""
This method is called by AJAX.  It checks opponents rolls when we call bullshit
check is for display.  real bullshit determination done in main
"""

def get_opponent_rolls(request):
  session_id = request.session.get('_auth_user_id', -1)
  if(session_id == -1):
    return login_page(request)
  print 'we made it to top of get_opponent_rolls!!'
  game_id = request.GET.get('game_id', 'NA')
  try:
    game = Game.objects.get(pk=game_id)
  except:
    game = -1
  if(game == -1):
    return render_to_response(index_page[platform],  csrf_request, context_instance=RequestContext(request))
  username = User.objects.get(pk=session_id)
  response = {}
  response['game_players'] = []
  response['player_dice_lists'] = []
  playing_cpu = int(request.GET.get('playing_cpu', 0))
  if(playing_cpu == 0):
    for player in game.players.all():
      up = UserProfile.objects.get(user=player)
      if(up.num_dice > 0 or str(player) == get_eliminated_player(game.log)):
        response['game_players'] += [str(player)]
        response['player_dice_lists'].append( get_player_dice_list(player) )
  else:
    print 'we\'re playing cpu, cpu_roll = %d' %game.cpu_roll
    up = UserProfile.objects.get(user=username)
    response['game_players'] += ['Cpu']
    response['player_dice_lists'].append(get_roll_from_int(game.cpu_roll)) 
    response['game_players'] += [str(username)]
    response['player_dice_lists'].append(get_roll_from_int(up.roll))
    
  json_str = simplejson.dumps(response)
  print 'get_opponents_rolls json_str:'
  print json_str
  return HttpResponse(json_str, mimetype='application/json') 

"""
This method exists solely to test no-refresh fuctionality
"""

def test_norefresh(request):
  return HttpResponse( mimetype='application/javascript')

'''
convert roll from singled concatenated integer into array
'''

def get_roll_from_int(roll_integer, num_dice=-1):
  print 'in get_roll_from_int'
  dice_list = []
  if(num_dice != -1):
    for i in range(num_dice):
      roll = (roll_integer%(10**(i+1)))/(10**i)
      roll_integer -= roll
      dice_list.append(roll)
  else:
    print 'num_dice not given'
    i = 0
    while (roll_integer != 0 and (i < 5)):
      roll = (roll_integer%(10**(i+1)))/(10**i)
      roll_integer -= (roll*(10**i))
      print 'roll = %d roll integer = %d' %(roll, roll_integer)
      dice_list.append(roll)
      i+=1
  return dice_list

"""
returns last roll of a given player
"""

def get_player_dice_list(player):
  up = UserProfile.objects.get(user=player)
  return get_roll_from_int(up.roll)

"""
determine whether previous player called bullshit
"""

def get_bullshit_call(log):
  if(log == ['']):
    return (False, '')
  log_array = re.split(r'\n', log)
  last_line = log_array.pop()
  while (last_line == '' and log_array != []):
    last_line = log_array.pop()
  if(re.search(r'Wrong|Correct|eliminated', last_line) != None):
    return (True, last_line)
  else:
    return (False, last_line)

"""
determine last claim amount/value
"""

def get_last_claim(log):
  print 'in get last claim'
  if(log == ['']):
    print 'first turn, no last claim'
    return (0, 0)
  log_array = re.split(r'\n', log)
  last_line = log_array.pop()
  while (last_line == '' and log_array != []):
    last_line = log_array.pop()
  line_re = re.search(r'claims\s+(?P<amount>\d+)\s+(?P<value>\d+)', last_line)
  if(line_re != None):
    #print 'claim found'
    #print 'amount:'
    #print line_re.groups('amount')[0]
    #print 'value:'
    #print line_re.groups('value')[0]
    return (line_re.group('amount'), line_re.group('value')[0])
  else:
    return (0,0)

"""
determine if last bs lead to an elimination, and if so, who
"""

def get_eliminated_player(log):
  print 'in get eliminated player'
  if(log == ['']):
    print 'first turn, no eliminated player'
    return ''
  log_array = re.split(r'\n', log)
  last_line = log_array.pop()
  while (last_line == '' and log_array != []):
    last_line = log_array.pop()
  line_re = re.search(r'(?P<loser>\S+)\s+eliminated', last_line)
  if(line_re != None):
    return line_re.group('loser')
  else:
    return ''

"""
method returns the game winner
"""
def get_winner(game):
  for player in game.players.all():
    player_profile = UserProfile.objects.get(user=player)
    if(player_profile.num_dice > 0):
      return string.upper(str(player))

def check_game_length(log):
  if(len(log) > 2300):
    return log[500:len(log)]

"""
this helper method allows us to get a param whether it is POST or GET
"""
def get_request_param(request, param, default):
  post_val = request.POST.get(param, default)
  if(post_val != default):
    print 'Post sata sent, param = %s' % param
    return post_val
  else:
    get_val = request.GET.get(param, default)
    return get_val
"""
helper method determines if we are on a mobile page
will have to change if intel ever gets a successful smartphone!!
"""

def get_platform(platform_string):
  if(re.search(r'86|Win32|Mac', platform_string)):
    return 'laptop'
  else:
    return 'mobile'

#"""
#helper method will attempt to return object based on pk.
#If it can't, it will redirect us to index.  It is useful
#for when user attempts to enter game that no longer exists
#"""
#def get_object_by_pk(input_db, key)
#  obj = input_db.objects.get(pk = key, -1)
#  if(obj == -1) {
    
