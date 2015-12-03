function GroupProjectBlockDashboardDetailsView(runtime, element) {
    var group_user_rows_selector_prefix = ".user-data-row.group_";
    var group_collapsed_icon_selector = '.group-collapsed-icon';
    var icons = {
        collapsed: "fa-caret-right",
        expanded: "fa-caret-down"
    };
    var data_attributes = {
        collapsed: 'collapsed',
        group_id: 'group-id'
    };
    var collapsed_values = {
        collapsed: 'collapsed',
        expanded: 'expanded'
    };

    function expand_group(group_label, group_id) {
        var group_user_rows_selector = group_user_rows_selector_prefix+group_id;
        $(group_label).data(data_attributes.collapsed, collapsed_values.expanded);
        $(group_user_rows_selector, element).show();
        $(group_collapsed_icon_selector, group_label).removeClass(icons.collapsed).addClass(icons.expanded);
    }

    function collapse_group(group_label, group_id) {
        var group_user_rows_selector = group_user_rows_selector_prefix+group_id;
        $(group_label).data(data_attributes.collapsed, collapsed_values.collapsed);
        $(group_user_rows_selector, element).hide();
        $(group_collapsed_icon_selector, group_label).removeClass(icons.expanded).addClass(icons.collapsed);
    }

    $(document).ready(function () {
        $(".group-label", element).click(function () {
            var group_id = $(this).data(data_attributes.group_id);
            var state = $(this).data(data_attributes.collapsed);

            if (state == collapsed_values.expanded) {
                collapse_group(this, group_id);
            }
            else{
                expand_group(this, group_id);
            }
        });
    });
}
