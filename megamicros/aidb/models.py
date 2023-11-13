# megamicros_aidb/apps/aidb/core/urls.py
#
# Copyright (c) 2023 Sorbonne Université
# Author: bruno.gas@sorbonne-universite.fr
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Megamicros AIDB models

MegaMicros documentation is available on https://readthedoc.biimea.io
"""

from datetime import date
from email.policy import default
from django.db import models
from django.conf import settings


class Config( models.Model ):
    host = models.URLField( 'Database host address', max_length=256, default='http://127.0.0.1' )
    dataset_path = models.CharField( 'Répertoire racine des datasets', max_length=256, default='/' )
    active = models.BooleanField( 'La configuration est active', default=True )
    comment = models.TextField( 'Notes', null=True )
    crdate = models.DateTimeField( 'creation date', auto_now_add=True )
    uddate = models.DateTimeField( 'last update date', null=True )

class Tagcat( models.Model ):
    name = models.CharField( 'Nom de la catégorie d\'étiquette', max_length=32 )
    comment = models.TextField( 'Notes', null=True )
    crdate = models.DateTimeField( 'creation date', auto_now_add=True )

    def __str__( self ):
        return f"{self.name}"


class Tag( models.Model ):
    name = models.CharField( 'Nom de l\'étiquette', max_length=32 )
    tagcat = models.ForeignKey( Tagcat, related_name='tags', on_delete=models.CASCADE )
    comment = models.TextField( 'Notes', null=True )
    crdate = models.DateTimeField( 'creation date', auto_now_add=True )

    def __str__( self ):
        return f"{self.name} ({self.tagcat})"

class Domain( models.Model ):
    name = models.CharField('Domain name', max_length=128 )
    comment = models.TextField( 'Notes', null=True )
    info = models.JSONField( 'Infos', null=True  )
    crdate = models.DateTimeField( 'creation date', auto_now_add=True )

    def __str__( self ):
        return '%s' % ( self.name )

class Device( models.Model ):
    name = models.CharField('Device name', max_length=128 )
    type = models.CharField('Device type', max_length=64 )
    identifier = models.CharField('Device identifier', max_length=128 )
    comment = models.TextField( 'Notes', null=True )
    info = models.JSONField( 'Infos', null=True  )
    crdate = models.DateTimeField( 'creation date', auto_now_add=True )

    def __str__( self ):
        return f"{self.name} (type {self.type}, id {self.identifier})"

class Campaign( models.Model ):
    name = models.CharField('Campaign name', max_length=128 )
    date = models.DateField( default=date.today )
    domain = models.ForeignKey( Domain, related_name='campaigns', on_delete=models.CASCADE )
    comment = models.TextField( 'Notes', null=True )
    info = models.JSONField( 'Infos', null=True  )
    crdate = models.DateTimeField( 'creation date', auto_now_add=True )

    def __str__( self ):
        return f"{self.name} ({self.date})"

class Directory( models.Model ):
    name = models.CharField( 'Nom local', max_length=256 )
    path = models.CharField( 'Chemin absolu (/data/...)', max_length=256 )
    campaign = models.ForeignKey( Campaign, related_name='directories', on_delete=models.CASCADE )
    device = models.ForeignKey( Device, related_name='directories', on_delete=models.CASCADE )
    comment = models.TextField( 'Notes', null=True )
    info = models.JSONField( 'Infos', null=True  )
    crdate = models.DateTimeField( 'creation date', auto_now_add=True )

    def __str__( self ):
        return f"{self.name}"

class Context( models.Model ) :
    PRIORI = 1
    POSTERIORI = 2
    TYPES = [
        (PRIORI, 'Contexte a priori'),
        (POSTERIORI, 'Contexte a posteriori')
    ]
    name = models.CharField( '(*) Nom du contexte', max_length=32 )
    code = models.CharField( '(*) Code', max_length=64 )
    type = models.SmallIntegerField( '(*) Type de contexte', choices=TYPES )
    domain = models.ForeignKey( Domain, related_name='contexts', on_delete=models.CASCADE )
    tags = models.ManyToManyField( Tag, related_name='contexts', blank=True )
    comment = models.TextField( 'Notes', null=True )
    info = models.JSONField( 'Infos', null=True  )
    crdate = models.DateTimeField( 'creation date', auto_now_add=True )
    parent = models.ForeignKey( 'self', related_name='children', on_delete=models.SET_NULL, null=True, blank=True )

    def __str__( self ):
        return f"{self.name}"

class Label( models.Model ) :
    name = models.CharField( '(*) Nom du label', max_length=32 )
    code = models.CharField( '(*) Code', max_length=64 )
    domain = models.ForeignKey( Domain, related_name='labels', on_delete=models.CASCADE )
    tags = models.ManyToManyField( Tag, related_name='labels', blank=True )
    comment = models.TextField( 'Notes', null=True )
    info = models.JSONField( 'Infos', null=True  )
    crdate = models.DateTimeField( 'creation date', auto_now_add=True )
    parent = models.ForeignKey( 'self', related_name='children', on_delete=models.SET_NULL, null=True, blank=True )

    def __str__( self ):
        return f"{self.name}"

class SourceFile( models.Model ):
    """
    Integrity field (bool) means whether or not the file is considered as ok.
    Default NULL value means that the file has not been checked.
    In case of integrity default, a message can be stored in the comment field 
    """
    H5 = 1
    MP4 = 2
    WAV = 3
    MUH5 = 4
    TYPES = [
        (H5, 'Fichier H5'),
        (MP4, 'Fichier vidéo mp4'),
        (WAV, 'Fichier son wav'),
        (MUH5, 'Fichier H5 au format Mu32')
    ]

    filename = models.CharField('(*) Nom du fichier', max_length=128 )
    type = models.SmallIntegerField( '(*) Type de données', choices=TYPES )
    datetime = models.DateTimeField( '(*) Date et heure de l\'enregistrement ' )
    duration = models.BigIntegerField( '(*) Durée de l\'enregistrement en microsecondes' )
    size = models.BigIntegerField( '(*) Taille du fichier en octets' )
    integrity = models.BooleanField( 'Le fichier est valide', null=True )
    directory = models.ForeignKey( Directory, related_name='files', on_delete=models.CASCADE )
    contexts = models.ManyToManyField( Context, through='FileContexting' )
    labels = models.ManyToManyField( Label, through='FileLabeling' )
    tags = models.ManyToManyField( Tag, blank=True )
    comment = models.TextField( 'Notes', null=True )
    info = models.JSONField( 'Infos', null=True  )
    crdate = models.DateTimeField( 'creation date', auto_now_add=True )

    def __str__( self ):
        return f"{self.filename} ({self.TYPES[self.type-1][1]})"

class FileContexting( models.Model ):
    #sourcefile = models.ForeignKey( SourceFile, related_name='contextings', on_delete=models.CASCADE )
    #context = models.ForeignKey( Context, related_name='files', on_delete=models.CASCADE )
    sourcefile = models.ForeignKey( SourceFile, on_delete=models.CASCADE )
    context = models.ForeignKey( Context, on_delete=models.CASCADE )
    datetime_start = models.FloatField( '(*) Timestamp du début du contexte' )
    datetime_end = models.FloatField( '(*) Timestamp de fin du context' )
    code = models.CharField('(*) Code unique', max_length=36 )
    comment = models.TextField( 'Notes', null=True )
    info = models.JSONField( 'Infos', null=True  )
    crdate = models.DateTimeField( 'creation date', auto_now_add=True )

    def __str__( self ):
        return f"[{self.datetime_start}, {self.datetime_end}]"


class FileLabeling( models.Model ):
    #sourcefile = models.ForeignKey( SourceFile, related_name='labelings', on_delete=models.CASCADE )
    #label = models.ForeignKey( Label, related_name='files', on_delete=models.CASCADE )
    sourcefile = models.ForeignKey( SourceFile, on_delete=models.CASCADE )
    label = models.ForeignKey( Label, on_delete=models.CASCADE )
    contexts = models.ManyToManyField( Context, blank=True )
    tags = models.ManyToManyField( Tag, related_name='filelabelings', blank=True )
    datetime_start = models.FloatField( '(*) Timestamp du début du label' )
    datetime_end = models.FloatField( '(*) Timestamp de fin du label' )
    code = models.CharField('(*) Code unique', max_length=36 )
    comment = models.TextField( 'Notes', null=True )
    info = models.JSONField( 'Infos', null=True  )
    crdate = models.DateTimeField( 'creation date', auto_now_add=True )

    def __str__( self ):
        return f"[{self.datetime_start}, {self.datetime_end}]"


class Dataset( models.Model ):
    name = models.CharField( '(*) Nom du dataset', max_length=128 )
    code = models.CharField( '(*) Code', max_length=64 )
    domain = models.ForeignKey( Domain, related_name='datasets', on_delete=models.CASCADE )
    labels = models.ManyToManyField( Label, blank=True )
    contexts = models.ManyToManyField( Context, blank=True )
    channels = models.JSONField( 'Voies (Mems)', default=list )
    filelabelings = models.ManyToManyField( FileLabeling, blank=True )
    filename = models.CharField( 'Nom du fichier de sauvegarde', max_length=128, null=True )
    tags = models.ManyToManyField( Tag, related_name='datasets', blank=True )
    comment = models.TextField( 'Notes', null=True )
    info = models.JSONField( 'Infos', null=True  )
    crdate = models.DateTimeField( 'creation date', auto_now_add=True )

    def __str__( self ):
        return f"{self.name}"