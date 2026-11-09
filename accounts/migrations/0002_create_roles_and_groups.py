from django.db import migrations


def create_roles_and_groups(apps, schema_editor):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    for app_config in global_apps.get_app_configs():
        create_permissions(app_config, verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    User = apps.get_model("accounts", "User")

    from accounts.permissions import ROLE_GROUPS, ROLE_PERMISSIONS

    group_map = {}
    for group_name, perms in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        group_map[group_name] = group
        perm_objs = []
        for app_label, codename in perms:
            p = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
            if p:
                perm_objs.append(p)
        group.permissions.set(perm_objs)

    for group_name in ROLE_GROUPS.values():
        if group_name not in group_map:
            group, _ = Group.objects.get_or_create(name=group_name)
            group_map[group_name] = group

    all_role_group_names = set(ROLE_GROUPS.values())

    # Sync existing users
    for user in User.objects.all():
        target_group_name = ROLE_GROUPS.get(user.role)
        current_groups = list(user.groups.filter(name__in=all_role_group_names))
        to_remove = [g for g in current_groups if g.name != target_group_name]
        if to_remove:
            user.groups.remove(*to_remove)
        if target_group_name:
            target_group = group_map.get(target_group_name)
            if target_group and target_group not in current_groups:
                user.groups.add(target_group)


def remove_roles_and_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    from accounts.permissions import ROLE_GROUPS
    Group.objects.filter(name__in=list(ROLE_GROUPS.values())).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("academics", "0002_initial"),
        ("grading", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_roles_and_groups, reverse_code=remove_roles_and_groups),
    ]
