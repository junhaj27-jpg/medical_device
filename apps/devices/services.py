from django.db.models import Count, Prefetch, Q

from .models import DeviceLot, MedicalDevice


def visible_devices(user):
    qs = MedicalDevice.objects.all()
    if user.role != "STAFF":
        return qs.prefetch_related("lots").annotate(visible_event_count=Count("events"))

    visible_lots = DeviceLot.objects.filter(events__reporter=user).distinct()
    return (
        qs.filter(events__reporter=user)
        .distinct()
        .prefetch_related(Prefetch("lots", queryset=visible_lots, to_attr="visible_lots"))
        .annotate(
            visible_event_count=Count(
                "events", filter=Q(events__reporter=user), distinct=True
            )
        )
    )
