from django.db import models
from jsonfield import JSONField

# Create your models here.
class InvertedIndex(models.Model):
	userID = models.IntegerField()
	invertedIndex = JSONField(null = True)
	lastPostTime = models.CharField(max_length=50, blank = True, null = True)
	numberOfPosts = models.IntegerField()
