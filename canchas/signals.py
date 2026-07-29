from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Cancha, AuditoriaCancha


@receiver(pre_save, sender=Cancha)
def auditar_cambio_cancha(sender, instance, **kwargs):
    if not instance.pk:
        return  # es una cancha nueva, no hay "cambio" que auditar

    try:
        anterior = Cancha.objects.get(pk=instance.pk)
    except Cancha.DoesNotExist:
        return

    cambio_precio = anterior.precio != instance.precio
    cambio_disponible = anterior.disponible != instance.disponible

    if cambio_precio or cambio_disponible:
        AuditoriaCancha.objects.create(
            cancha=instance,
            precio_anterior=anterior.precio if cambio_precio else None,
            precio_nuevo=instance.precio if cambio_precio else None,
            disponible_anterior=anterior.disponible if cambio_disponible else None,
            disponible_nuevo=instance.disponible if cambio_disponible else None,
        )