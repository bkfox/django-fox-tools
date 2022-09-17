from rest_framework import serializers


__all__ = ('ModelListSerializer',)


class ModelListSerializer(serializers.ListSerializer):
    """ Bulk create/update objects from provided instance """
    pk_attr = None
    """ Primary key attribute on validated data. """
    pk_field = 'pk'
    """ Primary key field on instance. """
    delete = True
    """ Delete missing objects on update. """
    
    def create(self, validated_data):
        model = self.child.Meta.model
        items = [model(**item) for item in validated_data]
        return model.objects.bulk_create(items)

    def update(self, instance, validated_data):
        pk_field = getattr(self.child.Meta, 'pk_field', self.pk_field)
        pk_attr = getattr(self.child.Meta, 'pk_attr', self.pk_attr or pk_field)

        db_map = {getattr(o, pk_field) for o in instance}
        data_map = {d[pk_attr] for d in validated_data if pk_attr in d}

        ret = []
        for id, data in data_map.items():
            obj = db_map.get(id)
            if obj is None:
                ret.append(self.child.create(data))
            else:
                ret.append(self.child.update(data))

        if self.delete:
            for id, obj in db_map.items():
                if id not in data_map:
                    obj.delete()
        return ret


