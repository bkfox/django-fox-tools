from rest_framework import serializers

from . import models


__all__ = ('TestSerializer', 'NameValueSerializer')


class TestSerializer(serializers.Serializer):
    name = serializers.CharField()
    value = serializers.IntegerField()


class NameValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NameValue
        fields = ('name','value')


