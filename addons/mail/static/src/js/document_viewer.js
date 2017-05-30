odoo.define('mail.DocumentViewer', function(require) {
    "use strict";

    var Widget = require('web.Widget');
    var core = require('web.core');
    var QWeb = core.qweb;

    var ZOOM_STEP = 0.5;

    var DocumentViewer = Widget.extend({
        template: "DocumentViewer",
        events: {
            'click .o_close_btn, .o_viewer_img_wrapper': '_onClose',
            'click .o_download_btn': '_onDownload',
            'click .o_viewer_img': '_onImageClick',
            'click .move_next': '_onNext',
            'click .move_previous': '_onPrevious',
            'click .o_zoom_in': '_onZoomIn',
            'click .o_zoom_out': '_onZoomOut',
            'keydown': '_onKeydown',
        },
        init: function(thread) {
            var attachment_ids = thread.get('attachment_ids');
            this.active_attachment = false;
            this.scale = 1;
            this.attachment_ids = _.filter(attachment_ids, function(attachment) {
                var type = attachment.mimetype.split('/').shift();
                if (type == 'image' || type == 'video') {
                    attachment.type = type;
                    return true;
                }
            });
        },
        renderContent: function() {
            this.$('.o_viewer_content').html(QWeb.render('DocumentViewer.Content', {
                widget: this
            }));
            this.scale = 1;
        },
        on_attachment_popup: function(attachment_id) {
            this.active_attachment = _.findWhere(this.attachment_ids, {
                id: attachment_id
            });
            this.renderElement();
            this.$el.modal('show');
            this.$el.on('hidden.bs.modal', _.bind(this._onDestroy, this));
        },
        _onClose: function(e) {
            e.preventDefault();
            this.$el.modal('hide');
        },
        _onDownload: function(e) {
            e.preventDefault();
            window.location = '/web/content/' + this.active_attachment.id + '?download=true';
        },
        _onImageClick: function(e) {
            e.stopPropagation();
        },
        _onZoom: function(scale) {
            if (scale > 0){
                this.$('.o_viewer_img').css('transform', 'scale3d(' + scale + ', ' + scale + ', 1)');
            }
        },
        _onZoomIn: function(e) {
            e.preventDefault();
            this.scale += ZOOM_STEP;
            this._onZoom(this.scale);
        },
        _onZoomOut: function(e) {
            e.preventDefault();
            this.scale -= ZOOM_STEP;
            this._onZoom(this.scale);
        },
        _onKeydown: function(e){
            switch (e.which) {
                case $.ui.keyCode.RIGHT:
                    this._onNext(e);
                    break;
                case $.ui.keyCode.LEFT:
                    this._onPrevious(e);
                    break;
            }
        },
        _onNext: function(e) {
            e.preventDefault();
            var index = _.findIndex(this.attachment_ids, this.active_attachment);
            index = index + 1;
            index = index % this.attachment_ids.length;
            this.active_attachment = this.attachment_ids[index];
            this.renderContent();
        },
        _onPrevious: function(e) {
            e.preventDefault();
            var index = _.findIndex(this.attachment_ids, this.active_attachment);
            index = index === 0 ? this.attachment_ids.length - 1 : index - 1;
            this.active_attachment = this.attachment_ids[index];
            this.renderContent();
        },
        _onDestroy: function() {
            if (this.isDestroyed()) {
                return;
            }
            this.$el.modal('hide');
            this.$el.remove();
        },
    });
    return DocumentViewer;
});