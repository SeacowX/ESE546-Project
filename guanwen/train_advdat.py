# -*- coding: utf-8 -*-
"""
Created on Fri Dec 16 22:46:03 2022

@author: nayut
"""
from torch import nn
from NLIDataset import NLIDataset
import torch
from torch.utils.data import DataLoader
from datasets import load_dataset, concatenate_datasets
from transformers import BertTokenizer, DistilBertTokenizer
from train import train_double_encoder, train_single_encoder, train_adv_cls, train_adv_dat
from models import BasicDoubleDistilBertClassifier, BasicSingleDistilBertClassifier, SameDistilBertClassifier, AdversialSameDistilBertClassifier, AdvDatSameDistilBertClassifier
import wandb
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(device)
snli_id_2_labels = {0:"entailment", 1:"neutral", 2:"contradictory"}
snli = load_dataset("snli").shuffle()
snli_train = concatenate_datasets([snli["train"], snli["validation"]]).filter(lambda x: x["label"] != -1)
snli_test = snli["test"].filter(lambda x: x["label"] != -1)
TRAINING_REQUIRED_LENGTH=25000
TESTING_REQUIRED_LENGTH=3000
#TOKENIZER = BertTokenizer.from_pretrained("bert-base-uncased")
TOKENIZER = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")
PERTURB_FRACTIONS = [0.2, 0.4,0.6]
alphas = [0.2,0.4,0.8]

for alpha in alphas:
    for PERTURB_FRACTION in PERTURB_FRACTIONS:
        
        snli_train_dataset = NLIDataset(snli_train["premise"][:TRAINING_REQUIRED_LENGTH], 
                                        snli_train["hypothesis"][:TRAINING_REQUIRED_LENGTH],
                                        snli_train["label"][:TRAINING_REQUIRED_LENGTH], 
                                        TOKENIZER,split=True, label_perturb=True, fraction=PERTURB_FRACTION, shuffle=False)
        snli_test_dataset = NLIDataset(snli_test["premise"][:TESTING_REQUIRED_LENGTH], 
                                       snli_test["hypothesis"][:TESTING_REQUIRED_LENGTH],
                                       snli_test["label"][:TESTING_REQUIRED_LENGTH], 
                                       TOKENIZER, split=True, label_perturb=True, fraction=0.5, shuffle=False)
        snli_test_dataloader = DataLoader(snli_test_dataset, batch_size=16, shuffle=True)
        snli_train_dataloader = DataLoader(snli_train_dataset, batch_size=16, shuffle=True)
        
        n_epochs = 1
        lr = 0.00001
        data_name = "snli"
        context = f"adv_dat_perturb_{PERTURB_FRACTION}_alpha_{alpha}"
        report_period = 100
        criterion = nn.CrossEntropyLoss()
        #adv_model = AdversialClassifier(alpha)
        model =  AdvDatSameDistilBertClassifier(alpha)
        lr_decay_factor = 0.97
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        decay_lambda = lambda epoch: lr_decay_factor ** epoch
        lr_scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda = decay_lambda)
        config = {"model_type": "Adversial_DAT_Single_distilbert" ,"learning_rate":lr, "training_data":data_name, "alpha":alpha,
                  "training_sample_size": TRAINING_REQUIRED_LENGTH, "perturbtion rate":PERTURB_FRACTION,
                  "testing_sample_size":TESTING_REQUIRED_LENGTH, "learning_rate_devay_factor":lr_decay_factor}
        wandb.init(project="ese546", config=config)
        wandb.watch(model)
        train_adv_dat(model, snli_train_dataloader, snli_test_dataloader, PERTURB_FRACTION, optimizer,
                      n_epochs, data_name, context, device, criterion, lr_scheduler, report_period=report_period)
