from django.db import models


class ImageFile(models.Model):
    title = models.CharField(max_length=225)
    image = models.FileField(blank=False, null=False)

    def __str__(self):
        return self.image.name


class ImageFolder(models.Model):
    title = models.CharField(max_length=225)
    folder = models.ImageField(blank=False, null=False)

    def __str__(self):
        return self.folder.name


class LayoutModel(models.Model):
    title = models.CharField(max_length=225)
    layout_model = models.FileField(blank=False, null=False)

    def __str__(self):
        return self.layout_model.name


class OCRModel(models.Model):
    title = models.CharField(max_length=225)
    ocr_model = models.FileField(blank=False, null=False)

    def __str__(self):
        return self.ocr_model.name


class OCRImage(models.Model):

    image_file = models.ForeignKey(ImageFile, related_name='ocr', on_delete=models.CASCADE)
    layout_model = models.ForeignKey(LayoutModel, related_name='ocr', on_delete=models.CASCADE)
    ocr_model = models.ForeignKey(OCRModel, related_name='ocr', on_delete=models.CASCADE)

    def __str__(self):
        return f'image {self.image_file}, ' \
               f'layout model {self.layout_model}, ' \
               f'ocr model {self.ocr_model}'


class OCRFolder(models.Model):

    image_folder = models.ForeignKey(ImageFolder, related_name='ocrfolder', on_delete=models.CASCADE)
    layout_model = models.ForeignKey(LayoutModel, related_name='ocrfolder', on_delete=models.CASCADE)
    ocr_model = models.ForeignKey(OCRModel, related_name='ocrfolder', on_delete=models.CASCADE)

    def __str__(self):
        return f'image folder {self.image_file}, ' \
               f'layout model {self.layout_model}, ' \
               f'ocr model {self.ocr_model}'
