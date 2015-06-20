from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save

# Create your models here.

class Game(models.Model):
  num_players = models.IntegerField()
  players = models.ManyToManyField(User)
  has_cpu = models.BooleanField() 
  cpu_roll = models.IntegerField()
  num_dice = models.IntegerField()
  num_cpu_dice = models.IntegerField()
  log = models.CharField(max_length=2500)
  turn = models.IntegerField()
  timestamp = models.IntegerField()

class GameRequest(models.Model):
  requested_players = models.IntegerField()
  accepted_players = models.IntegerField()
  player_names = models.ManyToManyField(User, related_name='+')
  host = models.OneToOneField(User) 
  has_cpu =  models.BooleanField()

class UserProfile(models.Model):
  user = models.OneToOneField(User)
  points = models.IntegerField()
  wins = models.IntegerField()
  losses = models.IntegerField()
  roll = models.IntegerField() 
  num_dice = models.IntegerField()
  turn = models.IntegerField()


def create_user_profile(sender, instance, created, **kwargs):
    """Create the UserProfile when a new User is saved"""
    if created:
        profile = UserProfile()
        profile.user = instance
        profile.points = 0
        profile.wins = 0
        profile.losses = 0
        profile.roll = 0
        profile.turn = 1
        profile.num_dice = 5
        profile.save()

post_save.connect(create_user_profile, sender=User)
