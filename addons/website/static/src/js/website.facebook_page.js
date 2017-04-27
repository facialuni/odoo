odoo.define('website.facebook_page', function (require) {


$(document).ready(function() {

    $('.o_facebook_page').each(function() {
        var params = $(this).data();
        if (params && params.href) {
            var actual_width = $(this).width();
            params.width = actual_width > 500 ? 500 : actual_width < 180 ? 180 : actual_width;
            var new_src = $.param.querystring('https://www.facebook.com/plugins/page.php', params);
            $(this).empty();
            $(this).append("<iframe src="+new_src+" width="+ params.width+" height="+ params.height+" style='border:none;overflow:hidden' scrolling='no' frameborder='0' allowTransparency='true'></iframe>");
        }
    });
});

});
