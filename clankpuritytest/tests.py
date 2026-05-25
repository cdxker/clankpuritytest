from django.test import TestCase
from django.urls import reverse

from .models import MetricsSnapshot


class HomeViewTests(TestCase):
    def test_home_returns_hello_world_html(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hello world")
