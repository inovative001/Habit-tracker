from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.utils import timezone
from django.db import models
from django.urls import reverse
from datetime import date, timedelta
from .models import Habit, HabitEntry


def home(request):
    """Public landing page. Redirect authenticated users to their dashboard."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'habits/home.html')


@login_required
def dashboard(request):
    """Personal dashboard showing only the logged-in user's habits."""
    selected_date_str = request.GET.get('date')
    if selected_date_str:
        try:
            selected_date = date.fromisoformat(selected_date_str)
        except ValueError:
            selected_date = timezone.localdate()
    else:
        selected_date = timezone.localdate()

    # Add a new habit for the logged-in user
    if request.method == 'POST' and 'name' in request.POST:
        name = request.POST.get('name', '').strip()
        if name:
            Habit.objects.create(user=request.user, name=name)
        return redirect('dashboard')

    habits = Habit.objects.filter(user=request.user).order_by('name')

    habit_data = []
    for habit in habits:
        entry = HabitEntry.objects.filter(habit=habit, date=selected_date).first()
        habit_data.append({
            'habit': habit,
            'entry': entry,
        })

    # Weekly review: last 7 days including selected_date
    week_start = selected_date - timedelta(days=6)
    week_entries = HabitEntry.objects.filter(
        habit__user=request.user,
        date__gte=week_start,
        date__lte=selected_date,
        status=HabitEntry.STATUS_DONE,
    ).values('habit').annotate(done_count=models.Count('habit'))

    # Monthly review: current month of selected_date
    month_start = selected_date.replace(day=1)
    month_entries = HabitEntry.objects.filter(
        habit__user=request.user,
        date__gte=month_start,
        date__lte=selected_date,
        status=HabitEntry.STATUS_DONE,
    ).values('habit').annotate(done_count=models.Count('habit'))

    week_counts = {e['habit']: e['done_count'] for e in week_entries}
    month_counts = {e['habit']: e['done_count'] for e in month_entries}

    # All-time progress totals per habit (kept = done, missed)
    all_done = HabitEntry.objects.filter(
        habit__user=request.user, status=HabitEntry.STATUS_DONE,
    ).values('habit').annotate(done_count=models.Count('habit'))
    all_missed = HabitEntry.objects.filter(
        habit__user=request.user, status=HabitEntry.STATUS_MISSED,
    ).values('habit').annotate(missed_count=models.Count('habit'))
    all_done_counts = {e['habit']: e['done_count'] for e in all_done}
    all_missed_counts = {e['habit']: e['missed_count'] for e in all_missed}

    # Attach counts to habit_data items for template access
    for item in habit_data:
        item['week_count'] = week_counts.get(item['habit'].id, 0)
        item['month_count'] = month_counts.get(item['habit'].id, 0)
        item['total_done'] = all_done_counts.get(item['habit'].id, 0)
        item['total_missed'] = all_missed_counts.get(item['habit'].id, 0)

    # Calculate days in week and month
    days_in_week = 7
    if selected_date.month == 12:
        next_month = selected_date.replace(year=selected_date.year + 1, month=1, day=1)
    else:
        next_month = selected_date.replace(month=selected_date.month + 1, day=1)
    days_in_month = (next_month - month_start).days

    context = {
        'selected_date': selected_date,
        'habit_data': habit_data,
        'days_in_week': days_in_week,
        'days_in_month': days_in_month,
    }
    return render(request, 'habits/dashboard.html', context)


def signup(request):
    """Sign up using Django's built-in UserCreationForm."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


@require_POST
@login_required
def toggle_status(request, habit_id, entry_date, status):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    entry_date_obj = date.fromisoformat(entry_date)

    if status not in ('done', 'missed'):
        return redirect('dashboard')

    entry, created = HabitEntry.objects.get_or_create(
        habit=habit,
        date=entry_date_obj,
        defaults={'status': status},
    )
    if not created:
        entry.status = status
        entry.save()

    return redirect(reverse('dashboard') + f"?date={entry_date_obj.isoformat()}")
