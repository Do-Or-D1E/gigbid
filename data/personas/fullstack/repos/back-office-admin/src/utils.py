from .models import Matter
from .serializers import MatterSerializer
from django.db import models
from rest_framework import permissions, viewsets


class Matter(models.Model):
    STATUS = [("new", "New"), ("paid", "Paid"), ("cancelled", "Cancelled")]

    reference = models.CharField(max_length=24, unique=True)
    owner = models.ForeignKey("auth.User", on_delete=models.PROTECT, related_name="matters")
    status = models.CharField(max_length=12, choices=STATUS, default="new", db_index=True)
    total_cents = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "status"])]

    def __str__(self):
        return f"{self.reference} ({self.status})"


class MatterViewSet(viewsets.ModelViewSet):
    serializer_class = MatterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Matter.objects.filter(owner=self.request.user).select_related("owner")
        status = self.request.query_params.get("status")
        return qs.filter(status=status) if status else qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
