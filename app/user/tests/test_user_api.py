from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse('users:create')
TOKEN_USER_URL = reverse('users:token')
ME_URL = reverse('users:me')


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """users api (public)"""

    def setUp(self):
        self.client = APIClient()

    def test_create_valid_user_success(self):
        """creating user with valid payload is successful"""
        payload = {
            'email': 'test@londonappdev.com',
            'password': 'testpass',
            'name': 'Test name'
        }
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(**res.data)
        self.assertEqual(user.get_username(), payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password', res.data)

    def test_user_exists(self):
        """create user which exists"""
        payload = {
            'email': 'test@example.com',
            'password': 'Password123',
            'name': 'Test Name'
        }
        create_user(**payload)

        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short(self):
        """password must be more than 5 chars"""
        payload = {
            'email': 'test@example.com',
            'password': 'Passw',
            'name': 'Test Name'
        }

        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """token is created for user"""
        payload = {
            'email': 'test@example.com',
            'password': 'Password123',
            'name': 'Test Name'
        }

        create_user(**payload)
        res = self.client.post(TOKEN_USER_URL, payload)
        # self.assertEqual(res.data.token, 'token')
        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_invalid_creds(self):
        """token is not created if invalid creds are given"""
        create_user(email='test@example.com', password='testpass')
        payload = {'email': 'test@example.com', 'password': 'wrongpass'}
        res = self.client.post(TOKEN_USER_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_no_user(self):
        """token is not created if user not exists"""
        payload = {
            'email': 'test@example.com',
            'password': 'Password123'
        }

        res = self.client.post(TOKEN_USER_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_missing_field(self):
        """email and password are required"""
        res = self.client.post(
            TOKEN_USER_URL, {'email': 'one', 'password': ''})
        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        """authentication is required"""
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTest(TestCase):
    """Test api requests that requires authentication"""

    def setUp(self):
        self.user = create_user(
            email='test@example.com',
            password='Test1234',
            name='Test User'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """retrieving profile for loggedin user"""
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            'email': self.user.email,
            'name': self.user.name
        })

    def test_not_allowed_post(self):
        """post are not allowed on me url"""
        res = self.client.post(ME_URL, {})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """updating the user profile for auth user"""
        payload = {'name': 'new name', 'password': 'newpass124'}

        res = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
