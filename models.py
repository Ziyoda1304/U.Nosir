from django.db import models


class Biography(models.Model):
    content = models.TextField(verbose_name="Hayoti va ijodi")

    class Meta:
        app_label = 'main'
        verbose_name = "Biografiya"
        verbose_name_plural = "Biografiya"

    def __str__(self):
        return "Usmon Nosir: Hayoti va ijodi"


class Work(models.Model):
    title = models.CharField(max_length=200, verbose_name="Asar nomi")
    txt_file = models.FileField(upload_to="asarlari/", verbose_name="TXT fayl")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'main'
        verbose_name = "Asar"
        verbose_name_plural = "Asarlar"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Feedback(models.Model):
    name = models.CharField("Ism", max_length=120)
    email = models.EmailField("Email", blank=True, null=True)
    message = models.TextField("Xabar")
    created_at = models.DateTimeField("Yuborilgan vaqt", auto_now_add=True)

    class Meta:
        app_label = 'main'
        verbose_name = "Fikr"
        verbose_name_plural = "Fikrlar"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.created_at:%Y-%m-%d %H:%M}"
