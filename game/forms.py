from django import forms

from .models import Run


class RunForm(forms.ModelForm):
    """Validates the stats the browser sends when a run ends.

    The player is never a field here: the view attaches request.user, so nobody can
    save a run for someone else. Bounds stop junk or absurd values from being stored.
    """

    seconds = forms.FloatField(min_value=0, max_value=600)
    distance = forms.FloatField(min_value=0, max_value=5000)
    attacks = forms.IntegerField(min_value=0, max_value=10000)
    hits = forms.IntegerField(min_value=0, max_value=10000)
    touched = forms.IntegerField(min_value=0, max_value=10000, required=False)
    banished = forms.BooleanField(required=False)

    class Meta:
        model = Run
        fields = ["seconds", "distance", "attacks", "hits", "touched", "banished"]

    def clean_touched(self):
        return self.cleaned_data.get("touched") or 0

    def clean(self):
        data = super().clean()
        if data.get("hits") is not None and data.get("attacks") is not None and data["hits"] > data["attacks"]:
            self.add_error("hits", "hits cannot exceed attacks")
        return data
