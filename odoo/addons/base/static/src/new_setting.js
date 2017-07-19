$(document).ready(function() {

    $('body').on('click', '.appContainer', function(event) {
        var settingName = $(event.currentTarget).attr('setting');
        $('.selected').removeClass('selected');
        $(event.currentTarget).addClass('selected');
        $('.show').addClass('o_hidden').removeClass('show');
        $('.' + settingName + '_setting_view').addClass('show').removeClass('o_hidden');
    });

    function hiliter(text, word) {
        if (text.indexOf('hiliterWord') !== -1) {
            text = text.replace('<span class="hiliterWord">', "");
            text = text.replace("</span>", "");
        }
        var match = text.search(new RegExp(word, "i"));
        word = text.substring(match, match+word.length);
        var hilitedWord = "<span class='hiliterWord'>" + word + '</span>';
        return text.replace(word,hilitedWord);
    }

    jQuery.expr[':'].contains = function(a, i, m) {
        return jQuery(a).text().toUpperCase()
            .indexOf(m[3].toUpperCase()) >= 0;
    };

    $('body').on('keyup', '.searchsettingtext', function(event) {
        var searchText = $('.searchsettingtext').val();
        var settingDiv = $('div[class*="_setting_view"]');
        settingDiv.each(function() {
            var mainDiv = this;
            if (searchText.length === 0) {
                $(this).find("h2").each(function() {
                    $(this).removeClass('o_hidden');
                });
                $(this).find('.o_settings_container').each(function() {
                    $(this).addClass('mt16');
                });
            } else {
                $(this).find("h2").each(function() {
                    $(this).addClass('o_hidden');
                });
                $(this).find('.o_settings_container').each(function() {
                    $(this).removeClass('mt16');
                });
            }

            var app = this.className.split(' ')[0].replace('_setting_view', "");
            var name = $('[setting=' + app + ']').html();
            if ($(this).find('.searchheader').length === 0) {
                $(this).prepend($("<h2>").html(name).addClass('searchheader'));
            } else {
                $(this).find('.searchheader').removeClass('o_hidden');
            }
            $(mainDiv).addClass('o_hidden');
            $(this).find(".o_setting_box").each(function() {
                var self = this;
                $(this).addClass('o_hidden');

                $(this).find("label:contains('" + searchText + "')").each(function() {
                    $(self).removeClass('o_hidden');
                    $(self).find('label').html(hiliter($(self).find('label').html(), searchText));
                    if (searchText.length != 0) {
                        $(mainDiv).removeClass('o_hidden');
                        $(mainDiv).find('.searchheader').removeClass('o_hidden');
                    } else {
                        $(mainDiv).addClass('o_hidden');
                        $(mainDiv).find('.searchheader').removeClass('o_hidden');
                    }

                    if ($(mainDiv).hasClass('show')) {
                        $(mainDiv).removeClass('o_hidden');
                        $(mainDiv).find('.searchheader').removeClass('o_hidden');
                    }

                    if (searchText.length == 0) {
                        $(mainDiv).find('.searchheader').addClass('o_hidden');
                    }
                });
            });
        });
    });
});
