from django.db import models

import uuid

class Book(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    genre = models.CharField(max_length=100)
    isbn = models.CharField(max_length=13, unique=True)
    total_copies = models.PositiveIntegerField()
    available_copies = models.PositiveIntegerField()
    issue_count = models.PositiveIntegerField(default=0)
    added_on = models.DateField(auto_now_add=True)

class IssueRecord(models.Model):
    issue_id = models.CharField(max_length=15, unique=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    member_name = models.CharField(max_length=255)
    member_id = models.CharField(max_length=50)
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, default='issued') # 'issued', 'returned'
    fine = models.PositiveIntegerField(default=0)
    renewed = models.BooleanField(default=False)
    renewal_date = models.DateField(null=True, blank=True)

class LibraryConfig(models.Model):
    fine_per_day = models.PositiveIntegerField(default=5)
