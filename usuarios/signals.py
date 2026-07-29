from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Usuario, AuditoriaRol


@receiver(pre_save, sender=Usuario)
def auditar_cambio_rol(sender, instance, **kwargs):
    if not instance.pk:
        return  # es un usuario nuevo, no hay "cambio" que auditar

    try:
        anterior = Usuario.objects.get(pk=instance.pk)
    except Usuario.DoesNotExist:
        return

    if anterior.rol != instance.rol:
        AuditoriaRol.objects.create(
            usuario=instance,
            rol_anterior=anterior.rol,
            rol_nuevo=instance.rol,
        )