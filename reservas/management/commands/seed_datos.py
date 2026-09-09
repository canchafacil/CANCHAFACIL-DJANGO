"""
Comando de gestión para poblar reservas y reseñas de ejemplo.

Uso:
    python manage.py seed_datos

Qué hace:
    1. Elimina TODAS las reservas y reseñas existentes.
    2. Toma la primera cancha real que encuentre en gestion_canchas.
    3. Crea 10 reservas con nombres variados:
       - 8 en fechas pasadas, estado 'completada', cada una CON su reseña
         (fecha de reseña coherente con la fecha de la reserva).
       - 2 en fechas futuras, estado 'confirmada', SIN reseña (no se puede
         reseñar algo que aún no ha pasado).

Colócalo en:
    reservas/management/commands/seed_datos.py
"""

from datetime import time, timedelta, datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from reservas.models import Reserva
from contacto.models import Resena
from gestion_canchas.models import Cancha


class Command(BaseCommand):
    help = "Elimina reservas/reseñas existentes y crea 10 reservas con nombres variados (8 pasadas con reseña, 2 futuras sin reseña)."

    def handle(self, *args, **options):
        hoy = timezone.localdate()

        # 1. Limpieza de datos anteriores
        total_resenas, _ = Resena.objects.all().delete()
        total_reservas, _ = Reserva.objects.all().delete()
        self.stdout.write(self.style.WARNING(
            f"Eliminadas {total_reservas} reservas y {total_resenas} reseñas previas."
        ))

        # 2. Cancha real existente
        cancha_obj = Cancha.objects.first()
        if cancha_obj is None:
            self.stderr.write(self.style.ERROR(
                "No hay ninguna cancha en la base de datos. Crea una antes de correr este comando."
            ))
            return

        nombre_cancha = cancha_obj.nombre
        precio_hora = cancha_obj.precio

        # 3. Personas de ejemplo (nombre, correo, teléfono)
        personas = [
            ("Camila Rojas",      "camila.rojas@example.com",   "3011234567"),
            ("Andrés Gómez",      "andres.gomez@example.com",   "3022345678"),
            ("Valentina Torres",  "valentina.torres@example.com","3033456789"),
            ("Julián Herrera",    "julian.herrera@example.com", "3044567890"),
            ("Mariana Castro",    "mariana.castro@example.com", "3055678901"),
            ("Santiago Ríos",     "santiago.rios@example.com",  "3066789012"),
            ("Laura Jiménez",     "laura.jimenez@example.com",  "3077890123"),
            ("Felipe Morales",    "felipe.morales@example.com", "3088901234"),
            ("Daniela Suárez",    "daniela.suarez@example.com", "3099012345"),
            ("Nicolás Peña",      "nicolas.pena@example.com",   "3100123456"),
        ]

        def crear_reserva(persona, fecha, horas_lista, estado, tipo_pago, monto_pagado, saldo_pendiente):
            nombre, correo, telefono = persona
            primera_hora_str = sorted(horas_lista)[0]
            h, m = map(int, primera_hora_str.split(':'))
            return Reserva.objects.create(
                nombre=nombre,
                correo=correo,
                telefono=telefono,
                fecha=fecha,
                hora=time(h, m),
                horas=horas_lista,
                cancha=nombre_cancha,
                duracion=f"{len(horas_lista)} horas" if len(horas_lista) != 1 else "1 hora",
                estado=estado,
                metodo_pago="Mercado Pago",
                precio_total=precio_hora * len(horas_lista),
                tipo_pago=tipo_pago,
                monto_pagado=monto_pagado,
                saldo_pendiente=saldo_pendiente,
            )

        def crear_resena(persona, reserva, jugador, cancha_tag, estrellas, texto, fecha_reserva, hora_resena):
            nombre, correo, _ = persona
            r = Resena.objects.create(
                nombre=nombre,
                correo=correo,
                jugador=jugador,
                cancha=cancha_tag,
                estrellas=estrellas,
                texto=texto,
                reserva=reserva,
            )
            # 'fecha' es auto_now_add, se fuerza después de crear
            Resena.objects.filter(pk=r.pk).update(
                fecha=timezone.make_aware(datetime.combine(fecha_reserva, hora_resena))
            )
            return r

        # --- 8 reservas PASADAS, completadas, cada una CON reseña ---
        datos_pasados = [
            # (dias_atras, horas, jugador, cancha_tag, estrellas, texto, hora_resena)
            (60, ["18:00", "19:00"], "Amateur",           "Fútbol 5",         5, "Excelente cancha, muy buen mantenimiento e iluminación. Volveremos pronto.", time(20, 30)),
            (52, ["17:00"],          "Semi-profesional",  "Fútbol 5",         4, "Buena experiencia en general, aunque esperamos unos minutos para entrar.", time(19, 15)),
            (45, ["20:00", "21:00"],"Profesional",        "Fútbol 8",         5, "Cancha en muy buen estado, el césped se siente muy parejo. Recomendada.", time(22, 10)),
            (38, ["16:00"],          "Amateur",           "Cancha múltiple",  3, "Está bien pero el vestuario podría mejorar un poco la limpieza.", time(17, 30)),
            (30, ["19:00"],          "Semi-profesional",  "Fútbol 5",         4, "Buena atención del personal, la reserva fue muy fácil de coordinar.", time(19, 15)),
            (21, ["18:00", "19:00"],"Amateur",            "Fútbol 8",         5, "Increíble ambiente para jugar con amigos, sin duda volveremos seguido.", time(20, 30)),
            (12, ["17:00", "18:00"],"Profesional",        "Cancha múltiple",  2, "La iluminación nocturna es bastante regular, se podría mejorar.", time(19, 15)),
            (5,  ["20:00"],         "Amateur",            "Fútbol 5",         5, "Todo excelente, cancha impecable y muy buena atención del personal.", time(21, 10)),
        ]

        for i, (dias, horas, jugador, cancha_tag, estrellas, texto, hora_resena) in enumerate(datos_pasados):
            persona = personas[i]
            fecha = hoy - timedelta(days=dias)
            reserva = crear_reserva(
                persona=persona,
                fecha=fecha,
                horas_lista=horas,
                estado=Reserva.ESTADO_COMPLETADA,
                tipo_pago=Reserva.TIPO_PAGO_COMPLETO if i % 2 == 0 else Reserva.TIPO_PAGO_ABONO,
                monto_pagado=precio_hora * len(horas) if i % 2 == 0 else precio_hora * Decimal('0.5'),
                saldo_pendiente=0 if i % 2 == 0 else precio_hora * Decimal('0.5'),
            )
            crear_resena(persona, reserva, jugador, cancha_tag, estrellas, texto, fecha, hora_resena)

        # --- 2 reservas FUTURAS, confirmadas, SIN reseña ---
        datos_futuros = [
            (15, ["16:00", "17:00"]),
            (30, ["18:00"]),
        ]

        for i, (dias, horas) in enumerate(datos_futuros):
            persona = personas[8 + i]
            fecha = hoy + timedelta(days=dias)
            crear_reserva(
                persona=persona,
                fecha=fecha,
                horas_lista=horas,
                estado=Reserva.ESTADO_CONFIRMADA,
                tipo_pago=Reserva.TIPO_PAGO_ABONO,
                monto_pagado=precio_hora,
                saldo_pendiente=precio_hora * (len(horas) - 1) if len(horas) > 1 else 0,
            )

        self.stdout.write(self.style.SUCCESS(
            f"Listo: {len(datos_pasados) + len(datos_futuros)} reservas creadas en la cancha '{nombre_cancha}' "
            f"({len(datos_pasados)} pasadas con reseña, {len(datos_futuros)} futuras sin reseña)."
        ))