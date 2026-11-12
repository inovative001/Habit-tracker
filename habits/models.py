from django.conf import settings
from django.db import models


class Habit(models.Model):
    name = models.CharField(max_length=200)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='habits')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class HabitEntry(models.Model):
    STATUS_DONE = 'done'
    STATUS_MISSED = 'missed'
    STATUS_CHOICES = [
        (STATUS_DONE, 'Done'),
        (STATUS_MISSED, 'Missed'),
    ]

    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='entries')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ('habit', 'date')

    def __str__(self):
        return f"{self.habit.name} - {self.date} - {self.status}"
