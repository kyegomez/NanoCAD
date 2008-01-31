// Copyright 2008 Nanorex, Inc.  See LICENSE file for details.

#ifndef ERRORDIALOG_H
#define ERRORDIALOG_H

#include <QWidget>

#include "Nanorex/Utility/NXLogger.h"
#include "Nanorex/Utility/NXCommandResult.h"
#include "Nanorex/Interface/NXNanoVisionResultCodes.h"
using namespace Nanorex;

#include "ui_ErrorDialog.h"

class ErrorDialog : public QDialog, private Ui_ErrorDialog {
	Q_OBJECT
	
public:
	ErrorDialog(const QString& message, NXCommandResult* commandResult = 0,
				QWidget *parent = 0);

	~ErrorDialog();

};

#endif
