from django.db import models
from jsonfield import JSONField

# Create your models here.
class InvertedIndex(models.Model):
	userID = models.IntegerField()
	invertedIndex = JSONField(null = True)
	lastPost = models.CharField(max_length=50, blank = True, null = True)
	
class Post (models.Model):
	userID = models.IntegerField()
	text = models.TextField()
	postID = models.CharField(max_length=50)