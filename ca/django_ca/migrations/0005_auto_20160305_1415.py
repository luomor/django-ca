# -*- coding: utf-8 -*-
# Generated by Django 1.9.3 on 2016-03-05 14:15
from __future__ import unicode_literals

import os

from django.db import migrations

from django_ca import ca_settings


def import_ca(apps, schema_editor):
    # get locations of possible public/private keys
    ca_crt = getattr(ca_settings, 'CA_CRT', None)
    if ca_crt is None:
        ca_crt = os.path.join(ca_settings.CA_DIR, 'ca.crt')

    ca_key = getattr(ca_settings, 'CA_KEY', None)
    if ca_key is None:
        ca_key = os.path.join(ca_settings.CA_KEY, 'ca.key')

    # Public or private key not present. The former case happens in initial migrations, the latter
    # case is a misconfiguration.
    if not os.path.exists(ca_crt) or not os.path.exists(ca_key):
        return

    # read public key
    with open(ca_crt) as stream:
        raw_crt = stream.read()

    # create a CA
    CertificateAuthority = apps.get_model('django_ca', 'CertificateAuthority')
    ca = CertificateAuthority.objects.create(name='Root CA', private_key_path=ca_key, pub=raw_crt)

    # move private key to correct location
    key_dir = os.path.dirname(ca_key)
    ca_key_new = os.path.join(key_dir, '%s.pem' % ca.serial)
    os.rename(ca_key, ca_key_new)

    # remove public key
    os.remove(ca_crt)

    # save changes
    ca.private_key_path = ca_key_new
    ca.save()



class Migration(migrations.Migration):

    dependencies = [
        ('django_ca', '0004_certificateauthority'),
    ]

    operations = [
        migrations.RunPython(import_ca),
    ]