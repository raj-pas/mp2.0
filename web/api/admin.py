from __future__ import annotations

from django.contrib import admin

from web.api import models

admin.site.register(models.Household)
admin.site.register(models.Person)
admin.site.register(models.Account)
admin.site.register(models.Holding)
admin.site.register(models.Goal)
admin.site.register(models.GoalAccountLink)
