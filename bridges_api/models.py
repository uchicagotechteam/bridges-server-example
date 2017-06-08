from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from rest_framework.authtoken.models import Token
from django.utils.text import slugify
from django.core.exceptions import ValidationError

import parser

gender_options = (('male', 'Male'), ('female', 'Female'))
profile_attributes = (
    ('gender', 'Gender'), ('ethnicity', 'Ethnicity'), ('position', 'Position'),
    ('current_employer', 'Current Employer'))

def ensure_unique(obj):
    obj.slug = slugify((obj.attribute + obj.value).replace(' ', ''))
    if (len(type(obj).objects.filter(slug=obj.slug)) != 0):
        raise ValidationError("%s is not unique" % obj.name)
    return obj


class DataFile(models.Model):
    data_file = models.FileField(upload_to='data/')

    def get_datasets(self):
        extension = self.data_file.name.split('.')[1]
        if extension in ('xlsx', 'xls'):
            csvFile = parser.convert_to_csv()

    @property
    def name(self):
        return self.data_file.name.split('/')[-1]

    def __unicode__(self):
        return self.name

    def clean(self):
        excel_filename = self.data_file.name
        extension = excel_filename.split('.')[1]
        if extension in ('xlsx', 'xls'):
            csvFile, csv_filepath = parser.convert_excel_to_csv(self.data_file)
            import pdb; pdb.set_trace()
            self.data_file.save(csv_filepath, csvFile)
        return self

class ParticipantAttribute(models.Model):
    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100, unique=True)
    average_salary = models.DecimalField(max_digits=7, decimal_places=4)
    num_participants = models.IntegerField()

    def __unicode__(self):
        return self.name

    def clean(self):
        return ensure_unique(self)

    class Meta:
        abstract = True

class Ethnicity(ParticipantAttribute):
    class Meta:
        verbose_name = 'Ethnicity'
        verbose_name_plural = 'Ethnicities'

class Position(ParticipantAttribute):
    pass

class Gender(ParticipantAttribute):
    pass

class Tag(models.Model):
    slug = models.CharField(max_length=50, unique=True)
    attribute = models.CharField(max_length=100, choices=profile_attributes)
    value = models.CharField(max_length=100)

    def __unicode__(self):
        return u'%s' % (self.value)

    def clean(self):
        return ensure_unique(self)

class Question(models.Model):
    title = models.CharField(max_length=300)
    owner = models.ForeignKey('UserProfile', related_name='userprofile',
    on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    answer = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    number_of_views = models.IntegerField(default=0)

    def __unicode__(self):
        return u'%s' % (self.title)

class UserProfile(models.Model):
    """
    Extends the native Django user model
    Look at https://goo.gl/fwZk1w for further explanation
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField()

    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=255, choices=gender_options)
    disabilities = models.CharField(max_length=255)
    ethnicity = models.CharField(max_length=255, blank=True)
    position = models.CharField(max_length=255, blank=True)
    current_employer = models.CharField(max_length=255, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True)

    def __unicode__(self):
        return self.full_name

    @property
    def full_name(self):
        return "%s %s" % (self.first_name, self.last_name)

    def save(self, *args, **kwargs):
       self.pk = self.user.pk
       super(UserProfile, self).save(*args, **kwargs)

class Employer(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=0, default=0)
    averagesalary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    questions = models.ManyToManyField(Question)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
   """
   Receiver is a decorator that activates an action when the native
   django user model has been saved. This lets us create a matching
   (empty) UserProfile whenever a user is created
   """
   if created and not instance.is_superuser:
       UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if not instance.is_superuser:
        instance.userprofile.save()

@receiver(post_save, sender=User)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
