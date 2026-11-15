"""Course platform for a coding bootcamp: main helpers."""

from .models import Student
from .serializers import StudentSerializer
from django.db import models
from rest_framework import permissions, viewsets


class Student(models.Model):
    STATUS = [("new", "New"), ("paid", "Paid"), ("cancelled", "Cancelled")]

    reference = models.CharField(max_length=24, unique=True)
    owner = models.ForeignKey("auth.User", on_delete=models.PROTECT, related_name="students")
    status = models.CharField(max_length=12, choices=STATUS, default="new", db_index=True)
    total_cents = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "status"])]

    def __str__(self):
        return f"{self.reference} ({self.status})"


class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Student.objects.filter(owner=self.request.user).select_related("owner")
        status = self.request.query_params.get("status")
        return qs.filter(status=status) if status else qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
