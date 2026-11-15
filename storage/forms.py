from django import forms


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        clean_file = super().clean
        if isinstance(data, (list, tuple)):
            if not data:
                return clean_file(data, initial)
            return [clean_file(file, initial) for file in data]
        return [clean_file(data, initial)]


class FileUploadForm(forms.Form):
    files = MultipleFileField(label="Files")