import lightning as L

#added imports
import torch
from torchmetrics import MetricCollection
from torchmetrics.classification import MulticlassAccuracy, MulticlassF1Score,MulticlassPrecision,MulticlassRecall, MultilabelAveragePrecision, MultilabelF1Score


class BaseModel(L.LightningModule):
    def __init__(self, args, datamodule, network):
        super().__init__()
        self.args = args

        self.model = network
        self.save_hyperparameters('args')
        
        self.datamodule = datamodule
        self.criterion = self.init_criterion()
        self.train_metric_collection = self.init_metrics()
        self.validation_metric_collection = self.init_metrics()
        self.test_metric_collection = self.init_metrics()

        self.training_step_outputs = []
        self.validation_step_outputs = []
        self.test_step_outputs = []

    def forward(self, x):
        return self.model(x)

    def training_step(self, batch, batch_idx):
        x, y = batch
        #TODO check whether flattening of x necessary?  probably not
        x_hat  = self.model(x) # timm models only return logits not probs
        batch_loss = self.criterion(x_hat, y)

        #turn logits to probabilities for logging
        if self.args.task == "slc":
            probabilities = torch.softmax(x_hat, dim=1)
        elif self.args.task == "mlc":
            probabilities = torch.sigmoid(x_hat)
        else:
            raise Exception("args.task not handled in training_step!")

        output = {"labels": y, "probabilities": probabilities, "loss": batch_loss}
        self.training_step_outputs.append(output)

        self.train_metric_collection.update(probabilities, y)

        return batch_loss #what we return is irrelevant in latest lightning version

    def validation_step(self, batch, batch_idx):
        x, y = batch
        x_hat  = self.model(x)
        batch_loss = self.criterion(x_hat, y)

        #turn logits to probabilities for logging
        if self.args.task == "slc":
            probabilities = torch.softmax(x_hat, dim=1)
        elif self.args.task == "mlc":
            probabilities = torch.sigmoid(x_hat)
        else:
            raise Exception("args.task not handled in validation_step!")

        output = {"labels": y, "probabilities": probabilities, "loss": batch_loss}
        self.validation_step_outputs.append(output)

        self.validation_metric_collection.update(probabilities, y)

        return output

    def test_step(self, batch, batch_idx):
        x, y = batch
        x_hat  = self.model(x)
        batch_loss = self.criterion(x_hat, y)

        #turn logits to probabilities for logging
        if self.args.task == "slc":
            probabilities = torch.softmax(x_hat, dim=1)
        elif self.args.task == "mlc":
            probabilities = torch.sigmoid(x_hat)
        else:
            raise Exception("args.task not handled in test_step!")

        output = {"labels": y, "probabilities": probabilities, "loss": batch_loss}
        self.test_step_outputs.append(output)

        self.test_metric_collection.update(probabilities, y)

        return output

    def on_train_epoch_end(self):
        """
        Log the tracked metrics for the trainingset after each epoch
        unpack the list of outputs and logs the respective metrics
        """
        self.log_dict(self.train_metric_collection.compute(), prog_bar=True)
        #TODO how do we discern train logs from val logs? -> VIA PREFIX!!! NOT IMPLEMENTED YET
        """ Compare with this approach... do we want additional strings in log
        metrics = self.validation_metric_collection(probabilities, labels)
        for name, value in metrics.items():
            self.log(f"val_{name}", value)
        """

        self.train_metric_collection.reset()
        self.training_step_outputs.clear()

    def on_validation_epoch_end(self):
        """
        Log the tracked metrics for the validation set after each epoch
        unpack the list of outputs and logs the respective metrics
        """
        self.log_dict(self.validation_metric_collection.compute(), prog_bar=True)

        self.validation_metric_collection.reset()
        self.validation_step_outputs.clear()

    def on_test_epoch_end(self):
        """
        Log after the training has finished 
            the test performance of the >>>>>BEST<<<<< model.
        unpack the list of outputs and logs the respective metrics
        """
        # TODO select the >>>>>BEST<<<<< model then compute&log like in train&val
            # best model through checkpoints? YES!!!! NOT IMPLEMENTED YET
            # does this necessiate change of train_step and val_step metric tracking
            # how many test epochs are there??? only one after multiple train&val epochs ?
                # TODO basiert es auf benchmark task?

        you give callbacks to the trainer

        model checkpoint to 

        use prefix for train_/val_/test_ so that names ae globally unique


        put model in untracked Files
        use modelcheckpoint
        self.test_metric_collection.reset()
        self.test_step_outputs.clear()

    ########################
    # CRITERION & OPTIMIZER
    ########################

    def configure_optimizers(self):
        optimizer = torch.optim.AdamW(lr=self.args.learning_rate,weight_decay=self.args.weight_decay)
        lr_scheduler = torch.optim.lr_scheduler.OneCycleLR(max_lr=self.args.max_lr,
                                                           epochs=self.args.epochs,
                                                           steps_per_epoch= len(self.datamodule.train_dataloader()),
                                                           pct_start=self.args.pct_start
                                                           )
        return {'optimizer': optimizer, 'lr_scheduler': lr_scheduler}

    def init_criterion(self):
        if self.args.task == "slc":
            criterion = torch.nn.CrossEntropyLoss()
        elif self.args.task == "mlc":
            criterion = torch.nn.BCEWithLogitsLoss()
        else:
            raise Exception("args.task not handled in init_criterion!")
        return criterion

    #################
    # LOGGING MODULE
    #################

    # implement functionality for logging here

    def init_metrics(self):

        num_classes = self.args.number_classes

        if self.args.task == "slc":

            self.best_metric = "f1_macro"

            #TODO PREFIX TODO PREFIX TODO PREFIX TODO PREFIX TODO PREFIX TODO PREFIX TODO PREFIX

            #Accuracy, F1Score, Precision and Recall in micro, macro and per class
            metrics_collection = MetricCollection({
                "accuracy_micro": MulticlassAccuracy(num_classes, average="micro"),
                "accuracy_macro": MulticlassAccuracy(num_classes, average="macro"),
                "accuracy_none": MulticlassAccuracy(num_classes, average="none"),
                "f1_micro": MulticlassF1Score(num_classes, average="micro"),
                "f1_macro": MulticlassF1Score(num_classes, average="macro"),
                "f1_none": MulticlassF1Score(num_classes, average="none"),
                "precision_micro": MulticlassPrecision(num_classes, average="micro"),
                "precision_macro": MulticlassPrecision(num_classes, average="macro"),
                "precision_none": MulticlassPrecision(num_classes, average="none"),
                "recall_micro": MulticlassRecall(num_classes, average="micro"),
                "recall_macro": MulticlassRecall(num_classes, average="macro"),
                "recall_none": MulticlassRecall(num_classes, average="none"),
            })
        elif self.args.task == "mlc":

            self.best_metric = "average_precision_macro"    #ASKED ask wether this is the best for multispectral mlc? yes we can choose between AP macro and micro

            #veragePrecision and F1Score in micro, macro and per class 
            metrics_collection = MetricCollection({
                "average_precision_micro": MultilabelAveragePrecision(num_classes, average="micro"),
                "average_precision_macro": MultilabelAveragePrecision(num_classes, average="macro"),
                "average_precision_none": MultilabelAveragePrecision(num_classes, average="none"),
                "f1_micro": MultilabelF1Score(num_classes, average="micro"),
                "f1_macro": MultilabelF1Score(num_classes, average="macro"),
                "f1_none": MultilabelF1Score(num_classes, average="none"),
            })
        else:
            raise Exception("args.task not handled!")
        
        return metrics_collection

    ####################
    # DATA RELATED HOOKS
    ####################

    def train_dataloader(self):
        return self.datamodule.train_dataloader()

    def val_dataloader(self):
        return self.datamodule.val_dataloader()

    def test_dataloader(self):
        return self.datamodule.test_dataloader()
