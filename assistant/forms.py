from django import forms


class SituationForm(forms.Form):
    """The game state the browser sends. Only numbers and flags: no free text from the
    player reaches the prompt, so there is nothing to prompt-inject."""

    phase = forms.ChoiceField(choices=[("running", "running"), ("ended", "ended")])
    time_left = forms.FloatField(min_value=0, max_value=600)
    seconds_total = forms.FloatField(min_value=1, max_value=600)
    distance = forms.FloatField(min_value=0, max_value=5000)
    attacks = forms.IntegerField(min_value=0, max_value=10000)
    hits = forms.IntegerField(min_value=0, max_value=10000)
    touched = forms.IntegerField(min_value=0, max_value=10000)
    entity_alive = forms.BooleanField(required=False)
    entity_distance = forms.FloatField(min_value=0, max_value=100)
    entity_ahead = forms.BooleanField(required=False, help_text="Entity is within ~45° of where the player faces")
    run_id = forms.IntegerField(required=False, min_value=1)
