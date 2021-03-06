# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-02-01 06:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Index',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('story_title', models.CharField(max_length=100, null=True)),
                ('story_link_main', models.CharField(max_length=100, null=True, unique=True)),
                ('story_author', models.CharField(max_length=50, null=True)),
                ('story_replytime', models.CharField(max_length=50, null=True)),
            ],
            options={
                'db_table': 'tianya_index',
            },
        ),
        migrations.CreateModel(
            name='Links',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('links', models.CharField(max_length=100, null=True, unique=True)),
            ],
            options={
                'db_table': 'tianya_links',
            },
        ),
        migrations.CreateModel(
            name='Story',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('story_mark', models.CharField(max_length=100)),
                ('story_replyid', models.IntegerField()),
                ('story_title', models.CharField(max_length=100, null=True)),
                ('story_author', models.CharField(max_length=50, null=True)),
                ('story_author_id', models.CharField(max_length=20, null=True)),
                ('story_link', models.CharField(max_length=100, null=True, unique=True)),
                ('story_posttime', models.CharField(max_length=50, null=True)),
                ('story_each_reply_time', models.CharField(max_length=50, null=True)),
                ('story_content', models.TextField()),
                ('story_content_md5', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'tianya_story',
            },
        ),
        migrations.AlterIndexTogether(
            name='story',
            index_together=set([('story_mark', 'story_replyid')]),
        ),
    ]
