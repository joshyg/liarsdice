#!/usr/bin/env python2.6
import sys
import re
import random
import math
from decimal import *
class LiarsDice:

  """
  returns probability of a given claim
  """
  def GetProbability(self, value, amount):
    #probability of roling value x >= n times with N dice 
    tmp_amount = amount - self.count[value-1] 
    if(tmp_amount > 0):
      result = 0
      N = self.num_dice - self.cpu_dice
      for n in range(tmp_amount, N + 1):
        combinations = Decimal(math.factorial(N))/Decimal((math.factorial(n)*math.factorial(N-n)))
        p_to_the_n = ((Decimal(1)/(3))**(n)) * ((Decimal(2)/(3))**(N-n))     
        result = result +  combinations*p_to_the_n
    else:
      result = 1
    print "probability of %d %d's is %.2f" % (amount, value, result)
    return result

  """
  determines if CPU believs claim to be bullshit
  """
  def GetBullShit(self):
    if(self.claim_value != 0 and self.claim_amount != 0):
      claim_probability =  Decimal(self.GetProbability(self.claim_value, self.claim_amount))
      #if the claim has better than 50/50 odds, dont call bullshit no matter what
      print "In GetBullShit, claim probability is %.2f" %(claim_probability)
      if(claim_probability > Decimal(1)/Decimal(2)):
        print "In GetBullShit claim has > .5 odds, cpu doesn't call bullshit"
        return 0
      values_array = [2,3,4,5,6]
      #step 1, see if we have a possible claim with probability > 1- claim_probability =  p[bullshit]
      for tmp_value in values_array:
        if(tmp_value <= self.claim_value):
          tmp_amount = self.claim_amount + 1 
        else:
          tmp_amount = self.claim_amount
        print "In GetBullShit tmp_value is %d tmp_amount is %d" % (tmp_value, tmp_amount)
        if(self.GetProbability(tmp_value, tmp_amount) >= 1-claim_probability):
          return 0
      return 1
    else:
      return 0
  
  """
  generate cpu claims, can also bluff
  """
  def GetCpuClaim(self):
    bluff = 0
    bluff_seed = random.randint(1,4)
    if(bluff_seed == 1):
      bluff = 1
      max_bluff = int(math.floor((Decimal(self.num_dice)/Decimal(2))))
      print "bluff_seed = 1, max_bluff = %d" %(max_bluff)
    #note: if max_bluff < self.claim_amount, then either the claim was outrageous (so we should have called bs) 
    #or we have a large amount of this value, in which case we should not bluff
    #6/10/2012: max bluff must be > self.claim_amount (as opposed to >=),
    # otherwise random.randint(self.claim_amount + 1, max_bluff) returns an error 
    if(bluff == 0 or max_bluff <= self.claim_amount):
      print "In GetCpuClaim, previous  claim_amount is %d previous claim_value is %d" % (self.claim_amount, self.claim_value)
      if(int(max(self.expectation_array)) > self.claim_amount):
        tmp_expectation_array = self.expectation_array
        tmp_expectation_array.pop(0)
        print "self.expectation_array"
        print self.expectation_array
        print "expectation_array"
        print tmp_expectation_array
        tmp_expectation_array.reverse()
        print "expectation_array"
        print tmp_expectation_array
        return [ 6-tmp_expectation_array.index(max(tmp_expectation_array)) , max(tmp_expectation_array) ]
      else:
        #simple
        #return [self.claim_value, self.claim_amount + 1]
        #more complex, find what we think is most probable, insonsiderate of their claim
        max_probability = 0
        values_array = [2,3,4,5,6]
        for tmp_value in values_array:
          if(tmp_value <= self.claim_value):
            tmp_amount = self.claim_amount + 1 
          else:
            tmp_amount = self.claim_amount
          tmp_probability = self.GetProbability(tmp_value, tmp_amount) 
          if(tmp_probability > max_probability):
            max_probability = tmp_probability
            max_amount = tmp_amount
            max_value = tmp_value
        return [max_value, max_amount ]
    else:
      print "bluffing"
      bluff_value = random.randint(2,6)
      bluff_amount = random.randint(self.claim_amount + 1, max_bluff) 
      return [bluff_value, bluff_amount]

  """
  method for inputing manual data and generating bullshit/claims
  """
  def PlayManualMode(self): 
    ##in manual mode we enter all values by hand, in addition to the previous claim
    self.cpu_dice = input("How many dice do you have?")
    self.num_dice = input("How many dice in the game?") 
    self.claim_value = 0
    self.claim_amount = 0
    self.cpu_claim_value = 0
    self.cpu_claim_amount = 0
    self.roll = []
    self.count = []
    self.expectation_array = []
    for i in range(self.cpu_dice) :
      tmp_string = "enter value of die %d => " %(i + 1)         
      tmp_die_roll = input(tmp_string)
      self.roll.append(tmp_die_roll)
    print "roll is:" 
    print self.roll
    for i in range(6) :
      self.count.append(self.roll.count(i+ 1) + self.roll.count(1))
      self.expectation_array.append(self.count[i] + math.floor((self.num_dice-self.cpu_dice)/3))
    first_turn = raw_input("First turn?") 
    if(first_turn != "yes" and first_turn != "y"):
      self.claim_value  = input("enter previous claim value")
      self.claim_amount = input("enter previous claim amount")
      if(self.GetBullShit()) :
        print "cpu says BullShit!!"
        bullshit_called = 1
        bullshit_called_by_cpu = 1
      else :
        [self.cpu_claim_value, self.cpu_claim_amount] = self.GetCpuClaim()
        print "CPU claims there are %d %d's" % (self.cpu_claim_amount,self.cpu_claim_value)
    else:
      [self.cpu_claim_value, self.cpu_claim_amount] = self.GetCpuClaim()
      print "CPU claims there are %d %d's" % (self.cpu_claim_amount,self.cpu_claim_value)

  """
  method for inputing data from web and generating bullshit/claims
  """
  def PlayWebMode(self): 
    ##in manual mode we enter all values by hand, in addition to the previous claim
    self.cpu_dice = self.request['cpu_dice']
    self.num_dice = self.request['num_dice']
    self.claim_value = 0
    self.claim_amount = 0
    self.cpu_claim_value = 0
    self.cpu_claim_amount = 0
    self.roll = []
    self.count = []
    self.expectation_array = []
    self.roll = self.request['roll']
    self.BullShit = False
    print "roll is:" 
    print self.roll
    for i in range(6) :
      self.count.append(self.roll.count(i+ 1) + self.roll.count(1))
      self.expectation_array.append(self.count[i] + math.floor((self.num_dice-self.cpu_dice)/3))
    first_turn = self.request['first_turn'] 
    if(first_turn != "yes" and first_turn != "y"):
      self.claim_value  = self.request['claim_value']
      self.claim_amount = self.request['claim_amount']
      if(self.GetBullShit()) :
        print "cpu says BullShit!!"
        bullshit_called = 1
        bullshit_called_by_cpu = 1
        self.BullShit = True 
      else :
        [self.cpu_claim_value, self.cpu_claim_amount] = self.GetCpuClaim()
        print "CPU claims there are %d %d's" % (self.cpu_claim_amount,self.cpu_claim_value)
    else:
      [self.cpu_claim_value, self.cpu_claim_amount] = self.GetCpuClaim()
      print "CPU claims there are %d %d's" % (self.cpu_claim_amount,self.cpu_claim_value)

  """
  Constructor
  """
  def __init__ (self, webmode=False, request = {}): 
    print "Welcome to Liars Dice!!"
    if(webmode):
      self.request = request
      self.PlayWebMode()
    else:
      ready_to_start = 0
      while (ready_to_start == 0) :
        manual_mode = raw_input("Would you like to play manual mode?")
        if(manual_mode != "yes" and manual_mode != "y"):
          self.num_players = input("How many players?")
          self.cpu_turn = input("What turn am I?")
          if(self.num_players < self.cpu_turn): 
            print "How can I be player %d when there are %d players?  try again" % (self.cpu_turn, self.num_players)
          else :
            ready_to_start = 1
            print "Ok, %d players, cpu is  player %d" % (self.num_players, self.cpu_turn)
        else:
          self.PlayManualMode()
            
      #roll dice
      self.cpu_dice = 5
      self.num_dice = 5*self.num_players
      self.aggressiveness_threshold = 1
      turn = 0
      #claim value = die number, claim amount = amount of instances the player claims it is occuring
      while (self.cpu_dice > 0 and self.num_dice > self.cpu_dice):
        bullshit_called = 0
        bullshit_called_by_cpu = 0
        self.claim_value = 0
        self.claim_amount = 0
        self.cpu_claim_value = 0
        self.cpu_claim_amount = 0
        self.roll = []
        self.count = []
        self.expectation_array = []
        for i in range(self.cpu_dice) :
          self.roll.append(random.randint(1,6))
        for i in range(6) :
          self.count.append(self.roll.count(i+ 1) + self.roll.count(1))
          self.expectation_array.append(self.count[i] + math.floor((self.num_dice-self.cpu_dice)/3))
        
        print "CPU Roll:" 
        print self.roll 
        print "CPU Count:" 
        print self.count 
        print "CPU expectation_array:" 
        print self.expectation_array
        while(bullshit_called == 0) :
          turn = (turn + 1)%self.num_players
          if(turn != 0):
            player = turn
          else:
            player = self.num_players
          if(turn == self.cpu_turn or turn == 0 and self.cpu_turn == self.num_players) :
            if(self.GetBullShit()) :
              print "cpu says BullShit!!"
              bullshit_called = 1
              bullshit_called_by_cpu = 1
            else :
              [self.cpu_claim_value, self.cpu_claim_amount] = self.GetCpuClaim()
              print "CPU claims there are %d %d's" % (self.cpu_claim_amount,self.cpu_claim_value)
          elif(self.cpu_claim_value != 0 or self.claim_value != 0):#ensures we dont ask for bs call on first turn
            tmp_string = "Would player %d like to call bullshit?" %(player)
            bullshit = raw_input(tmp_string)
            if(bullshit == "yes" or bullshit == "y"):
              bullshit_called = 1
            else:
              print("player %d enter die number") %(player)
              self.claim_value = input("=>") 
              print("player %d enter amount") %(player)
              self.claim_amount = input("=>")
          else:
            print("player %d enter die number") %(player)
            self.claim_value = input("=>") 
            print("player %d enter amount") %(player)
            self.claim_amount = input("=>")
        self.num_dice = self.num_dice - 1
        ##print "Roll:" 
        ##print roll 
        was_bullshit = raw_input("was it bullshit?")
        if(was_bullshit != "yes" and was_bullshit != "y") :
          if(bullshit_called_by_cpu):
            self.cpu_dice = self.cpu_dice - 1
        elif(turn == self.cpu_turn +1 or turn == 1 and self.cpu_turn == self.num_players):
          self.cpu_dice = self.cpu_dice - 1
      if(self.cpu_dice == 0):
        print "congratulations, you win"
      else:
        print "wow, you lost to the cpu, pretty lame"

if(__name__ == '__main__'):
  LiarsDiceObj = LiarsDice()
        
    
     
  
